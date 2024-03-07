import os
import re
import requests
import ee 
from tqdm import tqdm
import pandas as pd

from utils.utils import read_anchor_data, extract_zip, concat_reshape_delete_tif_s1, concat_reshape_delete_tif_s2, content_dispo, cloudFilter

# env setting and initialize gee connection
env_path = 'env/'
data_anchor_path = 'data/'
output_dir = "Sentinel-2A MSI"
date_info = 'date_info.csv'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

if os.path.exists(os.path.join(output_dir, date_info)):
    df_date_info = pd.read_csv(os.path.join(output_dir, date_info))
else:
    df_date_info = pd.DataFrame(columns=['date', 'file_name'])

service_account = 'your_credentials'
credentials = ee.ServiceAccountCredentials(
    service_account, 
    os.path.join(env_path, 'your_json') # if you run through notebook, you can use ee.Authenticate()
)
ee.Initialize(credentials)

# scope of searching point
start_date = '2023-02-01'
end_date = '2024-02-29'

# read anchor data
anchor_data = read_anchor_data(
    os.path.join(data_anchor_path, 'unique_object_and_coord.csv')
)

# list for storing the tif file
# used for deleting them, after concat them
tiff_files_li=['sentinel2_temp.B4.tif', 'sentinel2_temp.B3.tif', 
               'sentinel2_temp.B2.tif', 'sentinel2_temp.B8.tif']
bands_to_use = ['B4', 'B3', 'B2', 'B8']

dates_list = [] 
output_object_list = []

for _, i in tqdm(anchor_data[6400:8000].iterrows()):
    try:
        output_file = str(int(i['OBJECTID'])) + '.tif'
        centroid_lon = i['longitude']
        centroid_lat = i['latitude']
        half_width = 0.005    
        half_height = 0.005  
        # Calculate the bounding box based on the centroid
        pwj_bbox = ee.Geometry.Rectangle([centroid_lon - half_width, 
                                        centroid_lat - half_height, 
                                        centroid_lon + half_width, 
                                        centroid_lat + half_height])

        # Filter the Sentinel-2 Surface Reflectance Harmonized image collection
        collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterBounds(pwj_bbox) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',10))

        collection = collection.map(cloudFilter)

        # Get the first image in the filtered collection
        image = ee.Image(collection.first())

        # Get the date from the image
        acquisition_date = ee.Date(image.date()).format("YYYY-MM-dd").getInfo()

        if acquisition_date:
            dates_list.append(acquisition_date)
            output_object_list.append(output_file)
            # Select bands B4, B3, B2, and B8
            image = image.select(bands_to_use)

            # Get the projection of the image
            projection = image.projection()

            # Set the projection for the image
            image = image.setDefaultProjection(projection)

            # Define parameters for the download
            download_params = {
                'name': 'sentinel2_temp',  # Name for the image asset
                # 'scale': 3000,  # Adjust scale as needed
                'region': pwj_bbox
            }

            # Get the download URL for the image
            download_url = image.getDownloadURL(download_params)

            # Download the image
            response = requests.get(download_url)

            # Extract the filename from the Content-Disposition header
            content_disposition = response.headers['Content-Disposition']
            filename = re.findall('filename=(.+)', content_disposition)[0].replace('"', '')

            # Write the downloaded data to disk
            filename = extract_zip(filename, response)

            # Concatenate TIFF files and save the output
            output_path = os.path.join(output_dir, output_file)
            concat_reshape_delete_tif_s2(tiff_files_li, output_path, filename)
    except:
        # print(f"Unable to fetch object: {output_file}")
        continue

data = {
    'date': dates_list,
    'file_name': output_object_list
}
df = pd.DataFrame(data)
df_combined = pd.concat([df_date_info, df], ignore_index=True)
df_combined.to_csv(os.path.join(output_dir, date_info))