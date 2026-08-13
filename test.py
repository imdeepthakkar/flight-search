import datetime
from fast_flights import FlightQuery, Passengers, create_query, get_flights

# get tomorrow's date
tomorrow = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")

query = create_query(
    flights=[
        FlightQuery(
            date=tomorrow,
            from_airport="JFK",
            to_airport="LHR",
        ),
    ],
    seat="economy",
    trip="one-way",
    passengers=Passengers(adults=1),
    currency="USD",
)
res = get_flights(query)
print(res)
