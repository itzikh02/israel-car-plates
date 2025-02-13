import requests

BASIC_DB = "https://data.gov.il/api/3/action/datastore_search?resource_id=053cea08-09bc-40ec-8f7a-156f0677aff3&q="
MODELS_DB = "https://data.gov.il/api/3/action/datastore_search?resource_id=142afde2-6228-49f9-8a29-9b6c3a0cbe40&limit=1&q="
CAR_HISTORY_DB = "https://data.gov.il/api/3/action/datastore_search?resource_id=56063a99-8a3e-4ff4-912e-5966c0279bad&q="
DISABLED_DB = "https://data.gov.il/api/3/action/datastore_search?resource_id=c8b9f9c8-4612-4068-934f-d4acd2e3c06e&q="


def getData(car_number):
    # Get the basic information about the car
    response = requests.get(f"{BASIC_DB}{car_number}")
    if response.status_code == 200:
        if response.json()["result"]["total"] == 0:
            return
        else:
            basicData = response.json()["result"]["records"][0]
    else:
        print("Error:", response.status_code)
        return

    degem_nm = basicData["degem_nm"]

    # Get the car model details
    response = requests.get(f"{MODELS_DB}{degem_nm}")
    if response.status_code == 200:
        if response.json()["result"]["total"] == 0:
            modelData = 0

        else:
            modelData = response.json()["result"]["records"][0]
    else:
        print("Error:", response.status_code)
        return

    # Get the car history
    response = requests.get(f"{CAR_HISTORY_DB}{car_number}")
    if response.status_code == 200:
        if response.json()["result"]["total"] == 0:
            carHistoryData = 0

        else:
            carHistoryData = response.json()["result"]["records"][0]['kilometer_test_aharon']
    else:
        print("Error:", response.status_code)
        return

    # Get the disabled badge information
    response = requests.get(f"{DISABLED_DB}{car_number}")
    if response.status_code == 200:
        if response.json()["result"]["total"] == 0:
            disabledData = 0
        else:
            disabledData = 1
    else:
        print("Error:", response.status_code)
        return

    data_summary = {
        "basic": basicData,
        "model": modelData,
        "history": carHistoryData,
        "disabled": disabledData,

    }

    return data_summary



