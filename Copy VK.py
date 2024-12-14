import time
import requests
import configparser
import sys
import json
from tqdm import tqdm


config = configparser.ConfigParser()
config.read('settings.ini')
vk_token = config['Tokens']['Vk_token']
ya_disk_token = config['Tokens']['Ya_disk_token']
user_id = config['User']['user_id']


class VK:
    def __init__(self, access_token, version='5.199'):
        self.base_address = 'https://api.vk.com/method/'
        self.params = {
            'access_token': access_token,
            'v': version
        }

    def get_photos(self, user_id, extended=1, photo_sizes=1, count=5):
        url = f'{self.base_address}photos.get'
        params = {
            'owner_id': user_id,
            'extended': extended,
            'photo_sizes': photo_sizes,
            'album_id': 'profile',
            'count': count
        }
        params.update(self.params)
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Ошибка при получении фотографий: {response.text}")
            sys.exit(1)
        return response.json()


class YADisk:
    def __init__(self, folder_name, ya_disk_token):
        self.url = 'https://cloud-api.yandex.net/v1/disk/resources'
        self.ya_disk_token = ya_disk_token
        self.headers = {
            "Authorization": f"OAuth {self.ya_disk_token}"
        }
        self.folder_name = folder_name

    def create_folder(self):
        params = {"path": self.folder_name}
        response = requests.put(self.url, headers=self.headers, params=params)
        if response.status_code != 201:
            print(f"Не удалось создать папку на Яндекс.Диске: {response.text}")
            sys.exit(1)

    def upload_photo(self, photo_url, photo_name):
        upload_url = f"{self.url}/upload"
        params = {
            "path": f"{self.folder_name}/{photo_name}",
            "url": photo_url
        }
        response = requests.post(upload_url, headers=self.headers, params=params)
        if response.status_code != 202:
            print(f"Не удалось загрузить фотографию: {response.text}")
            sys.exit(1)

    def save_results_to_json(self, results, output_file="photos_info.json"):
        with open(output_file, "w") as outfile:
            json.dump(results, outfile, indent=4)


class WorkWithPhoto:
    def __init__(self, access_token, user_id, version='5.199'):
        self.user_id = user_id
        self.vk = VK(access_token, version)

    def __enter__(self):
        response = self.vk.get_photos(self.user_id, count=5)
        return response['response']['items']

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is IndexError:
            print('Произошла ошибка')
        return True


def max_get_photos(photos):
    unique_photos = []

    for photo in photos:
        sizes = sorted(photo["sizes"], key=lambda x: x["width"] * x["height"], reverse=True)
        max_size_photo = sizes[0]
        height = max_size_photo["height"]
        width = max_size_photo["width"]
        area = height * width

        unique_photos.append({
            "url": max_size_photo["url"],
            "width": width,
            "height": height,
            "likes_count": photo["likes"]["count"],
            "id": photo["id"],
            "area": area,
            "size_type": max_size_photo["type"]
        })

    unique_photos = sorted(unique_photos, key=lambda x: x["area"], reverse=True)
    return unique_photos[:6]


def write_to_file(unique_photos, output_file="photos_info.json"):
    written_in_file = []

    for photo in unique_photos:
        file_name = f"{photo['likes_count']}.jpg"
        size_type = photo['size_type']

        written_in_file.append({
            "file_name": file_name,
            "size": size_type
        })

    with open(output_file, "w") as outfile:
        json.dump(written_in_file, outfile, indent=4)


if __name__ == "__main__":
    folder_name = f'Photos_{user_id}'
    ya_disk = YADisk(folder_name, ya_disk_token)
    ya_disk.create_folder()

    with WorkWithPhoto(vk_token, user_id) as photos:
        max_photos = max_get_photos(photos)

        for photo in tqdm(max_photos, desc="Загрузка фотографий на Яндекс.Диск"):
            print(f"Загрузка {photo['id']} на Яндекс.Диск")
            ya_disk.upload_photo(photo['url'], f"{photo['likes_count']}.jpg")

    write_to_file(max_photos)