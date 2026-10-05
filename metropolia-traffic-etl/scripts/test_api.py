
import requests

# Chicago Traffic API
url = "https://data.cityofchicago.org/resource/gc7y-n4xa.json"

params = {
    "$limit": 5,
    "$order": "timestamp DESC"
}

try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    print("API berhasil diakses!")
    print(f"Jumlah data: {len(data)}")
    print("\nContoh data:")

    for row in data:
        print(row)

except requests.exceptions.RequestException as e:
    print(f"API gagal diakses: {e}")
  