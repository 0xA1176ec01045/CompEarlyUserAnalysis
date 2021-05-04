import web3
import pandas as pd
import json

w3 = web3.Web3(web3.Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR-PROJECT-ID'))

def isContract(address):
    code = w3.eth.getCode(address).hex()
    if code == '0x':
        return False
    else:
        return True


def isArgentWallet(address):
    abi = json.loads('[{"inputs":[{"internalType":"address","name":"_wallet","type":"address"}],"name":"isArgentWallet","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"}]')
    argentWalletDetector = w3.eth.contract(address='0xeca4B0bDBf7c55E9b7925919d03CbF8Dc82537E8', abi=abi)
    return argentWalletDetector.functions.isArgentWallet(address).call()


earlyUserFile = 'Compound.EarlyUsers.csv'
txData = pd.read_csv(earlyUserFile)

# Determine whether address type is either:
# --> User address (external owner account or EOA), or
# --> Contract address
addressType = []
counter = 0
for address in txData['address']:
    counter += 1
    if isContract(address):
        if isArgentWallet(address):
            addressType.append('EOA')
        else:
            addressType.append('contract')
    else:
        addressType.append('EOA')
txData['addressType'] = addressType
txData.to_csv('Compound.EarlyUsers.AccountType.csv',index=False)
