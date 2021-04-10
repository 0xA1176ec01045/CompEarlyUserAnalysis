import web3
import pandas as pd

w3 = web3.Web3(web3.Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR-PROJECT-ID'))

def isContract(address):
    code = w3.eth.getCode(address).hex()
    if code == '0x':
        return False
    else:
        return True

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
        addressType.append('contract')
    else:
        addressType.append('EOA')
txData['addressType'] = addressType
txData.to_csv('Compound.EarlyUsers.AccountType.csv',index=False)
