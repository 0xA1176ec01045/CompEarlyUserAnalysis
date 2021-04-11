import web3
import pandas as pd

#earlyUserFile = 'Compound.EarlyUsers.csv'
# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
# --> User must provide a valid Infura Project ID or replace with a local ethereum RPC 
w3 = web3.Web3(web3.Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR-PROJECT-ID'))

def isContract(address):
    code = w3.eth.getCode(address).hex()
    if code == '0x':
        return False
    else:
        return True

earlyUserFile = 'Compound.EarlyUsers.AccountType.csv'
earlyUserOutfile = 'Compound.EarlyUsers.InclIndirect.csv'
#earlyUserFile = 'unittest.allcontracttypes.csv'
#earlyUserOutfile = 'unittest.allcontracttypes.InclIndirect.csv'
txData = pd.read_csv(earlyUserFile)

# Remove withdraw and repay transactions from records;
# we are not using these in the calculation of multipliers anyway
supplyTxData    = txData[txData['action'] == 'supply']
borrowTxData    = txData[txData['action'] == 'borrow']
liquidateTxData = txData[txData['action'] == 'liquidate']
txData = pd.concat([supplyTxData,borrowTxData,liquidateTxData])

# If address is a contract, determine the requesting EOA;
# this step needs to be recursive in case of nested contract calls
contractTxData = txData[txData['addressType'] == 'contract']
while contractTxData['addressType'].str.contains('contract').any():
    for index, row in contractTxData.iterrows():
        if (row['addressType'] == 'contract'):
            # Overwrite contract address with calling address
            tx = w3.eth.getTransaction(row['txhash'])
            contractTxData.loc[index,'address'] = tx['from']
            # Update addressType if calling address is EOA
            if not isContract(tx['from']):
                contractTxData.loc[index,'addressType'] = 'EOA'

# Merge updated contract call records with direct protocol interaction records
userTxData = txData[txData['addressType'] == 'EOA']
txData = pd.concat([userTxData,contractTxData])
txData.to_csv(earlyUserOutfile,index=False)
