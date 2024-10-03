import requests
import asyncio
from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient


def get_data():
    data_response = requests.get('http://localhost:8081/fake_taxi_data')
    return data_response.text


connection_str = ''
eventhub_name = 'taxi_data_event'



async def run():
    # Create a producer client to send messages to the event hub.
    # Specify a connection string to your event hubs namespace and
    # the event hub name.
    while True:
        
        await asyncio.sleep(20)
    
        producer = EventHubProducerClient.from_connection_string(
            conn_str=connection_str, eventhub_name=eventhub_name)
        async with producer:
            # Create a batch.
            event_data_batch = await producer.create_batch()
            # Add events to the batch.
            event_data_batch.add(EventData(get_data()))
            # Send the batch of events to the event hub.
            await producer.send_batch(event_data_batch)
            print('Successfully sent to azure event hubs.')
            
asyncio.run(run())
