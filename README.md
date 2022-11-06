# Polygon API Access
A library for accessing the POLYGON API securely without exposing the Polygon API key.

### Installation
```
pip install polygon-api-access
```

### Get started
How to securely access the Polygon API without exposing the Polygon API key.

First import class portfolio and then use code of a similar logic to access the Polygon API to display results.

```Python
from polygon_api_access import PolygonAPIAccess
import os

polygonAPIAccess = PolygonAPIAccess()

currency_pairs = [["AUD","USD",[],portfolio("AUD","USD")]]

polygonAPIAccess = PolygonAPIAccess(os.getcwd(), "final_db")

print(polygonAPIAccess.access(currency_pairs))
```
