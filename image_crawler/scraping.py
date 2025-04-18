from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from PIL import Image
import pickle
import time
import os
from selenium.webdriver.common.by import By
import asyncio
import httpx
from io import BytesIO
from urllib.parse import unquote

cn_punc_list = [
    "。",  #// Period
    "？",  #// Question mark
    "！",  #// Exclamation mark
    "；",  #// Semicolon
    "：",  #// Colon
    "……", #// Ellipsis
    "——", #// Em dash (sometimes used for segmentation)
    "，"   #// Comma
]
def create_dir():
    isExist = os.path.exists(f"Ave_Mujica")
    if not isExist:
        os.mkdir(f"Ave_Mujica")
        os.mkdir(f"MyGo")

def retrieve_mujica_srcs():
    PATH = r"./chrome_driver/chromedriver.exe"
    print("___", PATH, "___")
    driver = webdriver.Chrome()
    driver.get("https://ave-mujica-images.pages.dev")
    elem = driver.find_element(By.TAG_NAME, "body")
    time.sleep(5)

    all_img = []
    urls = []
    alts = []

    no_of_pagedowns = 100
    new_imgs = 100 #arbitary number

    while no_of_pagedowns and new_imgs !=0:
        new_imgs = 0
        imgs = driver.find_elements(By.TAG_NAME, 'img')

        for img in imgs:

            url = img.get_attribute('src')
            alt = img.get_attribute("alt").replace(" ", "_")
            if (r'https://ave-mujica-images.pages.dev/assets/') in url and (url not in urls):
                urls.append(url)
                alts.append(alt)
                new_imgs += 1

        elem.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.5)
        no_of_pagedowns -= 1

        print(len(urls))

    img_srcs = list(zip(alts, urls))[1:]

    lines = []
    for img_src in img_srcs:
        alt, url = img_src
        lines.append(" | ".join([alt, url]))

    with open("Ave_Mujica/img_srcs.txt", "w+", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return img_srcs

def retrieve_mygo_srcs():
    PATH = r"C:/Users/user/PycharmProjects/pythonProject/image_crawler/chrome_driver/chromedriver.exe"
    print("___", PATH, "___")
    driver = webdriver.Chrome()
    driver.get("https://mygo.miyago9267.com/")
    elem = driver.find_element(By.TAG_NAME, "body")
    time.sleep(5)

    all_img = []
    urls = []
    alts = []

    no_of_pagedowns = 50
    new_imgs = 100 #arbitary number

    while no_of_pagedowns and new_imgs !=0:
        new_imgs = 1
        imgs = driver.find_elements(By.TAG_NAME, 'img')

        for img in imgs:
            url = unquote(img.get_attribute('src'))
            print(url)

            if (r'https://drive.miyago9267.com/d/file/img/mygo/') in url and (url not in urls):
                prefix, mid = url.split("/mygo/")
                mid, postfix = mid.split(".jpg")
                mid = mid.replace(" ", "_")
                urls.append(url)
                alts.append(mid)
                new_imgs += 1

        elem.send_keys(Keys.PAGE_DOWN)
        time.sleep(3)
        no_of_pagedowns -= 1

        print(len(urls))

    img_srcs = list(zip(alts, urls))[1:]

    lines = []
    for img_src in img_srcs:
        alt, url = img_src
        lines.append(" | ".join([alt, url]))

    with open("MyGo/img_srcs.txt", "w+", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return img_srcs

async def download_all_mujica_images():
    srcs_path = "Ave_Mujica/img_srcs.txt"
    with open(srcs_path, "r", encoding="utf-8") as f:
        urls = f.readlines()
    tasks = []
    for url in urls:
        description, url = url.split(" | ")
        tasks.append(download_an_image(url, description, origin="Ave_Mujica"))

    _ = await asyncio.gather(*tasks[900:1200])

async def download_all_mygo_images():
    srcs_path = "MyGo/img_srcs.txt"
    with open(srcs_path, "r", encoding="utf-8") as f:
        urls = f.readlines()
    tasks = []
    for url in urls:
        description, url = url.split(" | ")
        tasks.append(download_an_image(url, description, origin="MyGo"))

    _ = await asyncio.gather(*tasks[0:400])
async def download_an_image(url, description, origin="Ave_Mujica"):
    url = url.replace("\n", "")
    async with httpx.AsyncClient() as client:
        response = await client.get(url)#.replace("https", "http"))
        response.raise_for_status()  # Raise an exception for HTTP errors
        content = response.content

        image = Image.open(BytesIO(content))
        image = image.convert("RGB")
        #print(image)
        save_path = os.path.join(origin, f"{description}.jpg")
        print(save_path)
        image.save(save_path, "JPEG")

def main():
    create_dir()
    #srcs = retrieve_mujica_srcs()
    srcs = retrieve_mygo_srcs()
    for src in srcs:
        print(src)


if __name__ == "__main__":
    #main()
    asyncio.run(download_all_mujica_images())
    #asyncio.run(download_all_mygo_images())
