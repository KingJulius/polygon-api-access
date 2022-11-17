import datetime
import time
from polygon import RESTClient
from sqlalchemy import create_engine, text 
from math import isnan, sqrt
import requests

class PolygonAPIAccess:
    '''
    Instantiate the PolygonAPIAccess class and takes in 2 parameters.
    
    :param location: The file path to store the database
    :type location: str

    :param table_name: Name of the database
    :type table_name: str
    '''
    def __init__(self, location, table_name):
        # The api key given by the professor
        self.key = "beBybSi8daPgsTp5yx5cHtHpYcrjp5Jq"
        # location to store the db file
        self.db_location = location
        # Enter name of database
        self.table_name = table_name
        self.EMA = 0
        self.ATR = 0
        self.keltner_min_val = 0
        self.keltner_max_val = 0
        
    def send_response(self, from_, to, amount, precision):
        '''
        Open a RESTClient for making the api calls
        '''
        url = "https://api.polygon.io/v1/conversion/" + from_ + "/" + to + "?" + "amount=" + str(amount) + "&precision=" + str(precision) + "&apiKey=" + self.key
        response = requests.request("GET", url, headers={}, data={})
        if response.status_code == 200:
            return response.json()
        else:
            return None


    def ts_to_datetime(self, ts) -> str:
        '''
        Function slightly modified from polygon sample code to format the date string

        :param ts: Time Stamp
        :type ts: datetime.date

        :return: Formatted Time Stamp String
        :rtype: str
        '''
        return datetime.datetime.fromtimestamp(ts / 1000.0).strftime('%Y-%m-%d %H:%M:%S')


    def reset_raw_data_tables(self, engine, currency_pairs):
        '''
        Function which clears the raw data tables once we have aggregated the data in a 6 minute interval

        :param engine: Engine to connect to the database
        :type engine: sqlalchemy.future.engine.Engine

        :param currency_pairs: A dictionary defining the set of currency pairs we will be pulling data for
        :type currency_pairs: list
        '''
        with engine.begin() as conn:
            for curr in currency_pairs:
                conn.execute(text("DROP TABLE "+curr[0]+curr[1]+"_raw;"))
                conn.execute(text("CREATE TABLE "+curr[0]+curr[1]+"_raw(ticktime text, fxrate  numeric, inserttime text);"))
    
    def reset_raw_data_tables2(self, engine, currency_pairs):
        '''

        '''
        with engine.begin() as conn:
            for curr in currency_pairs:
                conn.execute(text("DROP TABLE "+curr[0]+curr[1]+"_raw2;"))
                conn.execute(text("CREATE TABLE "+curr[0]+curr[1]+"_raw2(min numeric, max  numeric, vol numeric, mean numeric, fd numeric);"))


    def initialize_raw_data_tables(self, engine, currency_pairs):
        '''
        This creates a table for storing the raw, unaggregated price data for each currency pair in the SQLite database

        :param engine: Engine to connect to the database
        :type engine: sqlalchemy.future.engine.Engine

        :param currency_pairs: A dictionary defining the set of currency pairs we will be pulling data for
        :type currency_pairs: list
        '''
        with engine.begin() as conn:
            for curr in currency_pairs:
                conn.execute(text("CREATE TABLE "+curr[0]+curr[1]+"_raw(ticktime text, fxrate  numeric, inserttime text);"))


    def initialize_raw_data_tables2(self, engine, currency_pairs):
        with engine.begin() as conn:
            for curr in currency_pairs:
                conn.execute(text("CREATE TABLE "+curr[0]+curr[1]+"_raw2(min numeric, max  numeric, vol numeric, mean numeric, fd numeric);"))
    
    
    def initialize_aggregated_tables(self, engine, currency_pairs):
        '''
        This creates a table for storing the (6 min interval) aggregated price data for each currency pair in the SQLite database

        :param engine: Engine to connect to the database
        :type engine: sqlalchemy.future.engine.Engine

        :param currency_pairs: A dictionary defining the set of currency pairs we will be pulling data for
        :type currency_pairs: list 
        '''
        with engine.begin() as conn:
            for curr in currency_pairs:
                conn.execute(text("CREATE TABLE "+curr[0]+curr[1]+"_agg(inserttime text, avgfxrate  numeric, stdfxrate numeric);"))


    def aggregate_raw_data_tables(self, engine, currency_pairs):
        '''
        This function is called every 6 minutes to aggregate the data, store it in the aggregate table, and then delete the raw data

        :param engine: Engine to connect to the database
        :type engine: sqlalchemy.future.engine.Engine

        :param currency_pairs: A dictionary defining the set of currency pairs we will be pulling data for
        :type currency_pairs: list
        '''
        with engine.begin() as conn:
            for curr in currency_pairs:
                result = conn.execute(text("SELECT AVG(fxrate) as avg_price, COUNT(fxrate) as tot_count FROM "+curr[0]+curr[1]+"_raw;"))
                for row in result:
                    avg_price = row.avg_price
                    tot_count = row.tot_count
                std_res = conn.execute(text("SELECT SUM((fxrate - "+str(avg_price)+")*(fxrate - "+str(avg_price)+"))/("+str(tot_count)+"-1) as std_price FROM "+curr[0]+curr[1]+"_raw;"))
                for row in std_res:
                    std_price = sqrt(row.std_price)
                date_res = conn.execute(text("SELECT MAX(ticktime) as last_date FROM "+curr[0]+curr[1]+"_raw;"))
                for row in date_res:
                    last_date = row.last_date
                conn.execute(text("INSERT INTO "+curr[0]+curr[1]+"_agg (inserttime, avgfxrate, stdfxrate) VALUES (:inserttime, :avgfxrate, :stdfxrate);"),[{"inserttime": last_date, "avgfxrate": avg_price, "stdfxrate": std_price}])
                
                # This calculates and stores the return values
                exec("curr[2].append("+curr[0]+curr[1]+"_return(last_date,avg_price))")
                
                if len(curr[2]) > 5:
                    try:
                        avg_pop_value = curr[2][-6].hist_return
                    except:
                        avg_pop_value = 0
                    if isnan(avg_pop_value) == True:
                        avg_pop_value = 0
                else:
                    avg_pop_value = 0
                
                # Calculate the average return value and print it/store it
                curr_avg = curr[2][-1].get_avg(avg_pop_value)
                
                # Now that we have the average return, loop through the last 5 rows in the list to start compiling the 
                # data needed to calculate the standard deviation
                for row in curr[2][-5:]:
                    row.add_to_running_squared_sum(curr_avg)
                
                # Calculate the standard dev using the avg
                curr_std = curr[2][-1].get_std()
                
                # Calculate the average standard dev
                if len(curr[2]) > 5:
                    try:
                        pop_value = curr[2][-6].std_return
                    except:
                        pop_value = 0
                else:
                    pop_value = 0
                curr_avg_std = curr[2][-1].get_avg_std(pop_value)
                
                # -------------------Investment Strategy-----------------------------------------------
                try:
                    return_value = curr[2][-1].hist_return
                except:
                    return_value = 0
                if isnan(return_value) == True:
                    return_value = 0

                try:
                    return_value_1 = curr[2][-2].hist_return
                except:
                    return_value_1 = 0
                if isnan(return_value_1) == True:
                    return_value_1 = 0

                try:
                    return_value_2 = curr[2][-3].hist_return
                except:
                    return_value_2 = 0
                if isnan(return_value_2) == True:
                    return_value_2 = 0

                try:
                    upp_band = curr[2][-1].avg_return + (1.5 * curr[2][-1].std_return)
                    if return_value >= upp_band and curr[3].Prev_Action_was_Buy == True and return_value != 0:   
                        curr[3].sell_curr(avg_price)
                except:
                    pass

                try:
                    loww_band = curr[2][-1].avg_return - (1.5 * curr[2][-1].std_return)
                    if return_value <= loww_band and curr[3].Prev_Action_was_Buy == False and return_value != 0:
                        curr[3].buy_curr(avg_price)
                except:
                    pass

    def aggregate_raw_data_tables2(self, engine, currency_pairs):

        with engine.begin() as conn:
            for curr in currency_pairs:
                avg = conn.execute(text("SELECT AVG(fxrate) AS avg_price FROM "+curr[0]+curr[1]+"_raw;"))
                for row in avg:
                    avg_price = row.avg_price
                    self.EMA = avg_price
                minvalue = conn.execute(text("SELECT MIN(fxrate) AS min_rate FROM "+curr[0]+curr[1]+"_raw;"))
                for row in minvalue:
                    min_rate = row.min_rate

                maxvalue = conn.execute(text("SELECT MAX(fxrate) AS max_rate FROM "+curr[0]+curr[1]+"_raw;"))
                for row in maxvalue:
                    max_rate = row.max_rate

                vol = conn.execute(text("SELECT MAX(fxrate)-MIN(fxrate) AS vol FROM "+curr[0]+curr[1]+"_raw;"))
                for row in vol:
                    vol_val = row.vol
                    self.ATR = vol_val

                fd = conn.execute(text("SELECT COUNT(*) AS tot_cnt FROM "+curr[0]+curr[1]+"_raw WHERE fxrate < " + str(self.keltner_min_val) + " or fxrate > " + str(self.keltner_max_val) + ";"))
                for row in fd:
                    fd_val = row.tot_cnt

                conn.execute(text("INSERT INTO "+curr[0]+curr[1]+"_raw2 (min, max, vol, mean, fd) VALUES (:min, :max, :vol, :mean, :fd);"),[{"min": min_rate, "max": max_rate, "vol": vol_val, "mean": avg_price, "fd": fd_val}])


   # def access(self, currency_pairs):
   #     '''
   #     This access function repeatedly calls the polygon api every 1 seconds for 24 hours 
   #     and stores the results.
   # 
   #     :param currency_pairs: A dictionary defining the set of currency pairs we will be pulling data for
   #     :type currency_pairs: list
   #     '''
   #     # Number of list iterations - each one should last about 1 second
   #     count = 0
   #     agg_count = 0
   #     
   #     # Create an engine to connect to the database; setting echo to false should stop it from logging in std.out
   #     engine = create_engine("sqlite+pysqlite:///{}/{}".format(self.db_location, self.table_name), echo=False, future=True)
   #     
   #     # Create the needed tables in the database
   #     self.initialize_raw_data_tables(engine,currency_pairs)
   #     self.initialize_aggregated_tables(engine,currency_pairs)
   #     
   # 
   #     # Loop that runs until the total duration of the program hits 24 hours. 
   #     while count < 86400: # 86400 seconds = 24 hours
   #             
   #         # Make a check to see if 6 minutes has been reached or not
   #         if agg_count == 360:
   #             # Aggregate the data and clear the raw data tables
   #             self.aggregate_raw_data_tables(engine,currency_pairs)
   #             self.reset_raw_data_tables(engine,currency_pairs)
   #             agg_count = 0
   #             
   #         # Only call the api every 1 second, so wait here for 0.75 seconds, because the 
   #         # code takes about .15 seconds to run
   #         time.sleep(0.75)
   #             
   #         # Increment the counters
   #         count += 1
   #         agg_count +=1
   # 
   #         # Loop through each currency pair
   #         for currency in currency_pairs:
   #             # Set the input variables to the API
   #             from_ = currency[0]
   #             to = currency[1]
   # 
   #             # Call the API with the required parameters
   #             resp = self.send_response(from_, to, amount=100, precision=2)
   #             if resp == None:
   #                 continue
   #
   #  
   #             # This gets the Last Trade object defined in the API Resource
   #             last_trade = resp["last"]
   # 
   #             # Format the timestamp from the result
   #             dt = self.ts_to_datetime(last_trade["timestamp"])
   # 
   #             # Get the current time and format it
   #             insert_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   #                 
   #             # Calculate the price by taking the average of the bid and ask prices
   #             avg_price = (last_trade['bid'] + last_trade['ask'])/2
   # 
   #             # Write the data to the SQLite database, raw data tables
   #             with engine.begin() as conn:
   #                 conn.execute(text("INSERT INTO "+from_+to+"_raw(ticktime, fxrate, inserttime) VALUES (:ticktime, :fxrate, :inserttime)"),[{"ticktime": dt, "fxrate": avg_price, "inserttime": insert_time}])
        
    
    def access(self, currency_pairs):
        '''
        This access function repeatedly calls the polygon api every 1 seconds for 24 hours 
        and stores the results.

        :param currency_pairs: A dictionary defining the set of currency pairs we will be pulling data for
        :type currency_pairs: list
        '''
        # Number of list iterations - each one should last about 1 second
        count = 0
        agg_count = 0
        
        # Create an engine to connect to the database; setting echo to false should stop it from logging in std.out
        engine = create_engine("sqlite+pysqlite:///{}/{}".format(self.db_location, self.table_name), echo=False, future=True)
        
        # Create the needed tables in the database
        self.initialize_raw_data_tables(engine,currency_pairs)
        self.initialize_raw_data_tables2(engine,currency_pairs)
        
        # Saving all the keltner band values
        keltner_upper_band = []
        keltner_lower_band = []

        # Loop that runs until the total duration of the program hits 24 hours. 
        while count < 86400: # 86400 seconds = 24 hours
                
            # Make a check to see if 6 minutes has been reached or not
            if agg_count == 360:
                # Aggregate the data and clear the raw data tables
                self.keltner_max_val = self.EMA + count*0.025*self.ATR
                self.keltner_min_val = self.EMA - count*0.025*self.ATR
                keltner_upper_band.append(self.keltner_max_val)
                keltner_lower_band.append(self.keltner_min_val)
                self.aggregate_raw_data_tables2(engine,currency_pairs)
                self.reset_raw_data_tables(engine,currency_pairs)
                agg_count = 0
                
            # Only call the api every 1 second, so wait here for 0.75 seconds, because the 
            # code takes about .15 seconds to run
            time.sleep(0.75)
                
            # Increment the counters
            count += 1
            agg_count +=1

            # Loop through each currency pair
            for currency in currency_pairs:
                # Set the input variables to the API
                from_ = currency[0]
                to = currency[1]

                # Call the API with the required parameters
                resp = self.send_response(from_, to, amount=100, precision=2)
                if resp == None:
                    continue

                # This gets the Last Trade object defined in the API Resource
                last_trade = resp["last"]

                # Format the timestamp from the result
                dt = self.ts_to_datetime(last_trade["timestamp"])

                # Get the current time and format it
                insert_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                # Calculate the price by taking the average of the bid and ask prices
                avg_price = (last_trade['bid'] + last_trade['ask'])/2

                # Write the data to the SQLite database, raw data tables
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO "+from_+to+"_raw(ticktime, fxrate, inserttime) VALUES (:ticktime, :fxrate, :inserttime)"),[{"ticktime": dt, "fxrate": avg_price, "inserttime": insert_time}])
        
    
