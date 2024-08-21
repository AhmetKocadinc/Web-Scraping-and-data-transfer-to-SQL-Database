from bs4 import BeautifulSoup
import requests
import pandas as pd
from sqlalchemy import create_engine
import psycopg2
import re


data = {}

for i in range(1, 51):
    url = "https://www.emlakjet.com/satilik-konut/manisa/" + str(i) + ""
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "lxml")

    s1 = soup.find_all('div', attrs={'class': '_3qUI9q'})

    for div in s1:
        head = div.find("a", attrs={"class": "_3qUI9q"})
        if head is not None:
            links_second = head.get("href")
            if links_second:
                first_link = "https://www.emlakjet.com/"
                links = first_link + links_second

                detail = requests.get(links)
                detail_soup = BeautifulSoup(detail.content, "lxml")

                details_of_home = detail_soup.find_all("div", attrs={"class": "_2HQCBI"})
                if details_of_home:
                    for details in details_of_home:
                        all_details = details.find_all("div", attrs={"class": "_35T4WV"})
                        if all_details:
                            for i in all_details:
                                label_div = i.find("div", attrs={"class": "_1bVOdb"})
                                if label_div is not None:
                                    label_text = label_div.text.strip()
                                    value_div = label_div.find_next_sibling("div", attrs={"class": "_1bVOdb"})
                                    if value_div is not None:
                                        value_text = value_div.text.strip()
                                        if label_text in data:
                                            data[label_text].append(value_text)
                                        else:
                                            data[label_text] = [value_text]

                price_detail_div = detail_soup.find("div", attrs={"class": "_2TxNQv"})
                if price_detail_div:
                    price_text = price_detail_div.text.strip()
                    if "Fiyat" in data:
                        data["Fiyat"].append(price_text)
                    else:
                        data["Fiyat"] = [price_text]

                adress_detail = detail_soup.find("div", attrs={"class": "_3VQ1JB"})
                if adress_detail:
                    full_adress = adress_detail.find("p").text.strip()
                    if "Adress" in data:
                        data["Adress"].append(full_adress)
                    else:
                        data["Adress"] = [full_adress]

# Liste uzunluklarını eşitleme
max_length = max(len(v) for v in data.values())
for key in data:
    while len(data[key]) < max_length:
        data[key].append(None)  # Eksik değerler için None ekleniyor

# Sözlükten DataFrame'e dönüştürme
df = pd.DataFrame(data)

# Fiyatta yazan karışıklığın giderilmesi

df['Fiyat'] = df['Fiyat'].apply(lambda x: re.sub(r'[^\d,]', '', x).replace(',', ''))
df['Fiyat'] = df['Fiyat'].astype(str).apply(lambda x: x[:-1] if x[-1] != '0' else x)
df['Fiyat'] = df['Fiyat'].astype(int)

# Dataframe check etme

def check_df(data):
    print(data.head(), '\n')
    print(data.tail(), '\n')
    print(data.shape, '\n')
    print(data.info(), '\n')
    print(data.isnull().sum(), '\n')


check_df(df)

# Boşlukların doldurulması

df["Görüntülü Gezilebilir mi?"] = df["Görüntülü Gezilebilir mi?"].fillna("Hayır")
df["WC Sayısı"] = df["WC Sayısı"].fillna(1)
df["Yatırıma Uygunluk"] = df["Yatırıma Uygunluk"].fillna("Bilinmiyor")
df["Balkon Sayısı"] = df["Balkon Sayısı"].fillna(1)
df["Eşya Durumu"] = df["Eşya Durumu"].fillna("Boş")
df["Takas"] = df["Takas"].fillna("Yok")
df["Balkon Durumu"] = df["Balkon Durumu"].fillna("Var")
df["Balkon Tipi"] = df["Balkon Tipi"].fillna("Açık Balkon")
df["Yapı Durumu"] = df["Yapı Durumu"].fillna("İkinci El")
df["Yapı Tipi"] = df["Yapı Tipi"].fillna("Betonarme")
df["Tapu Durumu"] = df["Tapu Durumu"].fillna("Kat İrtifakı")
df["Zemin Etüdü"] = df["Zemin Etüdü"].fillna("Var")

# Gerek olmayan sütunların silinmesi

df.drop(["İpotek Durumu","Kira Getirisi","Aidat","İpotek Durumu","Balkon Metrekare","Ada","Parsel","Banyo Metrekare","Salon Metrekare","WC Metrekare","Pafta","Balkon Tipi Kapalı Teras", "Kattaki Daire Sayısı"], axis=1, inplace=True)

df.dropna(inplace=True)

# 'Adres' sütununu ayırma
df[['İl', 'İlçe', 'Mahalle']] = df['Adress'].str.split(' - ', expand=True)

# 'Mahalle' sütunundan 'Mahallesi' kelimesini kaldırma
df['Mahalle'] = df['Mahalle'].str.replace(' Mahallesi', '', regex=False)

# Adresi düzenledikten sonra hepsi bir arada yazan sütunun kaldırılması

df.drop("Adress",axis=1, inplace=True)

# Metrekare ölçülerinin düzenlenmesi

df['Brüt Metrekare'] = df['Brüt Metrekare'].str.extract(r'(\d+)').astype(int)

df.at[2, 'Net Metrekare'] = 6800

# Veri biçimlerinin düzenlenmesi

numeric_columns = ["İlan Numarası", "Net Metrekare", "Banyo Sayısı", "Balkon Sayısı", "WC Sayısı", "Binanın Kat Sayısı", "Fiyat"]
df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')

# Dataframe i veritabanına yazdırma

from sqlalchemy import create_engine

username = 'postgres'
password = '1234'
host = 'localhost'
port = '5432'
database = 'manisa_home'

engine = create_engine(f'postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}')

df.to_sql('emlak_ilanlari', engine, index=False, if_exists='replace')

print("DataFrame başarıyla PostgreSQL veritabanına yazıldı!")


