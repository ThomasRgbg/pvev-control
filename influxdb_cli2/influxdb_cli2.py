# 
# V1 Something to start with...
# V2 Handle force parameter better
# V3 Remove timezone information and convert to UTC... 
# V4 code review from someone smarter than me.
#

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

from datetime import datetime, timedelta, timezone
import logging
logging.basicConfig(format='influxdb_cli2: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)



class influxdb_cli2:
    def __init__(self, influxdb_url, token, org, bucket, debug = False):
        self.influxdb_client = influxdb_client.InfluxDBClient(url=influxdb_url, token=token, org=org)
        self.bucket=bucket
        self.org = org
        self.debug = debug

        logger.setLevel(logging.DEBUG if debug else logging.INFO)

        self.write_api = self.influxdb_client.write_api(write_option=SYNCHRONOUS)

    def write_sensordata(self, location, measurement, value, timestamp = None, force = None):
        if value is None:
            return
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        logger.debug("Got sample: location: {0}, measurement: {1}, value {2}, timestamp {3}".format(location,measurement,value, timestamp))

        try:
            value = float(value)
        except (ValueError, TypeError) as e:
            logger.warning("Discarding sample, could not convert value to float: location={0}, measurement={1}, value={2!r}, error={3}".format(
                    location, measurement, value, e))
            return

        if not force:
            if value == 0.0:
                logger.debug("discarding value, since zero")
                return

        write_data = [
            {
                'measurement': measurement,
                'tags': {
                    'location': location
                },
                'fields': {
                    'value': value
                },
                'time' : timestamp.isoformat()
            }
        ]
        logger.debug("write to influxdb: {0}".format(write_data))

        try:
            self.write_api.write(self.bucket, self.org, write_data)
        except influxdb_client.rest.ApiException as e:
            logger.warning("InfluxDB write failed: location={0}, measurement={1}, status={2}, reason={3}".format(
                location, measurement, e.status, e.reason))
        except Exception as e:
            logger.warning("Unexpected error writing to InfluxDB: {0}".format(e))


    # working query
    # from(bucket: "home/autogen")
    #  |> range(start: v.timeRangeStart, stop:v.timeRangeStop)
    #  |> filter(fn: (r) => r._measurement == "Battery_Power" and r.location == "pv_fronius")

    def _flux_escape(self, value):
        """Escape a string for safe use inside a double-quoted Flux string literal."""
        return str(value).replace('\\', '\\\\').replace('"', '\\"')


    def query_data(self, location, measurement, start_date, end_date):
        start_date = start_date.astimezone(timezone.utc).replace(tzinfo=None)
        start_date = start_date.isoformat(sep='T', timespec='seconds')
        end_date = end_date.astimezone(timezone.utc).replace(tzinfo=None)
        end_date = end_date.isoformat(sep='T', timespec='seconds')

        query_api = self.influxdb_client.query_api()

        query = '''
            from(bucket: "{bucket}")
            |> range(start: {start}Z, stop: {stop}Z)
            |> filter(fn: (r) => r._measurement == "{measurement}")
        '''.format(
            bucket=self.bucket,
            start=start_date,
            stop=end_date,
            measurement=self._flux_escape(measurement),
        )

        if location is not None and location != '':
            query += '        |> filter(fn: (r) => r.location == "{location}")\n'.format(
                location=self._flux_escape(location)
            )

        logger.debug("Query: {0}".format(query))

        result = query_api.query(query=query)
        result = result.to_values(columns=['_time', 'location', '_measurement', '_value'])

        logger.debug("Result: {0}".format(result))
        return result
