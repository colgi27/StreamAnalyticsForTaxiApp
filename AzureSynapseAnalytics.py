from azure.storage.blob import BlobServiceClient
import pyodbc
import pandas as pd
import joblib
import io
import json


### load the model

connection_string = 'DefaultEndpointsProtocol=https;AccountName=taxidata1stacc;AccountKey=2jyi7UxdLYusxkTLHcbdCr3QtmBLNkxejvWhhwhJiP0xs/twOcs9kWAHcWvdpBc8twi0L0tkUiif+ASt8osi3g==;EndpointSuffix=core.windows.net'
container_name = 'trainedmlmodel'
blob_name = "random_forest_model.pkl"
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service_client.get_container_client(container_name)
blob_client = container_client.get_blob_client(blob_name)
blob_data = blob_client.download_blob()
content = blob_data.readall()
model = joblib.load(io.BytesIO(content))

## read the data from synapse

server = 'synapse-for-taxi-app.sql.azuresynapse.net'
database = 'taxi_db'  
username = 'sqladminuser'  
password = 'Alina@12345'  
driver = '{ODBC Driver 18 for SQL Server}'

connection_string_odbc = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
conn = pyodbc.connect(connection_string_odbc)

query = "SELECT * from taxi_db.ml_mart"
df = pd.read_sql(query,conn)
conn.close()
df.columns = [column.lower() for column in df.columns]

## predict

feature_names = model.feature_names_in_
categorical_features = ['booking_source', 'time_of_day', 'day_of_week', 'weather_conditions', 'traffic_conditions']
fake_df_encoded = pd.get_dummies(df, columns=categorical_features, drop_first=True)
fake_df_encoded = fake_df_encoded.reindex(columns=feature_names, fill_value=0)
probs = model.predict_proba(fake_df_encoded)  # Probabilities for both classes
df['prob_of_cancellation'] = probs[:,0]


## load back the data

json_string = df.to_json(orient='records', lines=True)
json_objects = json_string.strip().split('\n')
parsed_objects = []
for json_obj_str in json_objects:
    parsed_obj = json.loads(json_obj_str)
    parsed_objects.append(parsed_obj)

output_file_path = 'predictions.json'
with open(output_file_path, 'w') as json_file:
    json.dump(parsed_objects, json_file, indent=4)


container_name='predictions'
blob_name = 'predictions.json'

list_of_messages = json.dumps(parsed_objects)
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service_client.get_container_client(container_name)
blob_client = container_client.get_blob_client(blob_name)
blob_client.upload_blob(list_of_messages)

print(f"Uploaded file to {blob_client.url}")