import zipfile 
import re 

import tifftools
import tifffile

import geemap
import folium 
import numpy as np 
import pandas as pd
pd.set_option('display.max_columns', None)
import seaborn as sns
import matplotlib.pyplot as plt


def read_anchor_data(dir):
    return pd.read_csv(dir)

def extract_zip(filename, response):
    with open(filename, 'wb') as f:
        f.write(response.content)

    # Unzip the downloaded archive
    with zipfile.ZipFile(filename, "r") as zip_ref:
        zip_ref.extractall()
    return filename

def concat_reshape_delete_tif_s1(tiff_list, output_path, filenames):
    tifftools.tiff_concat(tiff_list, output_path, overwrite=True)
    # 
    # tiff_file = tifffile.imread(output_path)
    # tiff_file = tiff_file.transpose([2,0,1])
    # tifftools.write_tiff('output.tif', tiff_file)
    # Delete the extracted files and the ZIP archive
    for i in set(tiff_list):
        os.remove(i)
    for j in set(filenames):
        os.remove(j)
    print("Download completed.")

def concat_reshape_delete_tif_s2(tiff_list, output_path, filename):
    tifftools.tiff_concat(tiff_list, output_path, overwrite=True)
    # tiff_file = tifffile.imread(output_path)
    # tiff_file = tiff_file.transpose([2,0,1])
    # tifftools.write_tiff('output.tif', tiff_file)
    # Delete the extracted files and the ZIP archive
    for i in tiff_list:
        os.remove(i)
    os.remove(filename)

    print("Download completed.")

def content_dispo(response):
    content_disposition = response.headers['Content-Disposition']
    filename = re.findall('filename=(.+)', content_disposition)[0].replace('"', '')
    filename = extract_zip(filename, response)
    return filename

def cloudFilter(image):
    # Get the QA60 band, which contains cloud information
    qa = image.select('QA60')
    # Bits 10 and 11 are clouds and cirrus clouds, respectively
    cloudBitMask = 1 << 10
    cirrusBitMask = 1 << 11
    # Combine both bit masks
    mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(
        qa.bitwiseAnd(cirrusBitMask).eq(0))
    # Return the image with the cloud mask applied
    return image.updateMask(mask)