import finnhub

class StocksAPI:
    def __init__(self, apiKey):
        self.configuration = finnhub.Configuration( api_key={ 'token': apiKey } )
        self.client = finnhub.DefaultApi(finnhub.ApiClient(self.configuration))
        return


class Wallet:
    def __init__(self, balance):
        self.balance = balance
        return

stocks  = StocksAPI('brvjlgvrh5rd378r30f0')
Wallet  = Wallet(1000.0)