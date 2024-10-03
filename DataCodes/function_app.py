import azure.functions as func
from azure.storage.blob import BlobServiceClient
import pyodbc
import pandas as pd
import joblib
import io
import json
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="http_trigger_tester_function",methods=["POST"])
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        ### Load the model from blob storage
        connection_string = 'DefaultEndpointsProtocol=https;AccountName=taxidata1stacc;AccountKey=2wHy8vV5811jt6gWMbv37JMH+XNh09DbkCmCElLIJC8mdJBKhPE8lq6yK1QnTNH7qSqzbItFKmt5+AStvnXHeQ==;EndpointSuffix=core.windows.net'
        container_name = 'trainedmlmodel'
        blob_name = "random_forest_model.pkl"
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_data = blob_client.download_blob()
        content = blob_data.readall()
        model = joblib.load(io.BytesIO(content))

        ## Read data from Synapse (SQL)
        server = 'synapse-for-taxi-app.sql.azuresynapse.net'
        database = 'taxisqlpool'
        username = 'taxisqladminuser2'
        password = 'Alina@12345'
        driver = '{ODBC Driver 18 for SQL Server}'

        connection_string_odbc = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(connection_string_odbc)
        query = "SELECT * FROM taxi_db.ml_mart"
        df = pd.read_sql(query, conn)
        conn.close()
        df.columns = [column.lower() for column in df.columns]

        ## Prediction
        feature_names = model.feature_names_in_
        categorical_features = ['booking_source', 'time_of_day', 'day_of_week', 'weather_conditions', 'traffic_conditions']
        df_encoded = pd.get_dummies(df, columns=categorical_features, drop_first=True)
        df_encoded = df_encoded.reindex(columns=feature_names, fill_value=0)
        probs = model.predict_proba(df_encoded)
        df['prob_of_cancellation'] = probs[:, 0]

        ## Save results back to Blob storage
        json_string = df.to_json(orient='records', lines=True)
        json_objects = json_string.strip().split('\n')
        parsed_objects = [json.loads(obj_str) for obj_str in json_objects]

        container_name = 'predictions'
        blob_name = 'predictions.json'
        blob_client = blob_service_client.get_blob_client(container_name, blob_name)
        blob_client.upload_blob(json.dumps(parsed_objects),overwrite=True)

        logging.info(f"Uploaded predictions to {blob_client.url}")

        return func.HttpResponse(f"Predictions uploaded successfully to {blob_client.url}")

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"An error occurred: {str(e)}", status_code=500)
