import pandas as pd
import web3
import json
import requests
from sys import argv

earlyUserFile = 'CompoundV2.EarlyUserEvents.AccountTypes.csv'
outfile = 'CompoundV2.EarlyUserInterest.csv'
txData = pd.read_csv(earlyUserFile,
            names=['block','txhash','address','action','token','decimals',
                   'amount','ctokenamt'])

tokenList = ['ZRX','BAT','REP','WETH','SAI','ETH','USDC','WBTC','DAI']

# cToken contract metadata
# Only includes contracts deployed before block 9601359 (release of COMP)
cZRX = {
  "address"     : '0xB3319f5D18Bc0D84dD1b4825Dcde5d5f7266d407',
  "deployBlock" : 7710735,
  "abi"         : 'cZRX.abi.json'
}
cBAT = {
  "address"     : '0x6C8c6b02E7b2BE14d4fA6022Dfd6d75921D90E4E',
  "deployBlock" : 7710735,
  "abi"         : 'cBAT.abi.json'
}
cSAI = {
  "address"     : '0xF5DCe57282A584D2746FaF1593d3121Fcac444dC',
  "deployBlock" : 7710752,
  "abi"         : 'cSAI.abi.json'
}
cREP = {
  "address"     : '0x158079Ee67Fce2f58472A96584A73C7Ab9AC95c1',
  "deployBlock" : 7710755,
  "abi"         : 'cREP.abi.json',
}
cETH = {
  "address"     : '0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5',
  "deployBlock" : 7710758,
  "abi"         : 'cETH.abi.json',
}
cUSDC = {
  "address"     : '0x39AA39c021dfbaE8faC545936693aC917d5E7563',
  "deployBlock" : 7710760,
  "abi"         : 'cUSDC.abi.json',
}
cWBTC = {
  "address"     : '0xC11b1268C1A384e55C48c2391d8d480264A3A7F4',
  "deployBlock" : 8163813,
  "abi"         : 'cWBTC.abi.json'
}
cDAI = {
  "address"     : '0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643',
  "deployBlock" : 8983575,
  "abi"         : 'cDAI.abi.json'
}
cTokens = [cZRX,cBAT,cSAI,cREP,cETH,cUSDC,cWBTC,cDAI]

def get_cToken_address(cToken):
    '''Return the address associated with the specified cToken'''
    #print(cToken)
    for token in cTokens:
        if cToken == token['abi'].split('.')[0]:
            return token['address']
    return '0x'

#def get_cToken_abi(cToken):
#    '''Return the ABI associated with the specified cToken'''
#    #print(cToken)
#    for token in cTokens:
#        if cToken == token['abi'].split('.')[0]:
#            return token['abi']
#    return '0x'
#
#def get_cToken_underlying(cToken):
#    '''Return the label associated with the underlying token'''
#    #print(cToken)
#    for token in cTokens:
#        if cToken == token['abi'].split('.')[0]:
#            return token['abi'].split('.')[0].split('c')[1]

# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
w3 = web3.Web3(web3.Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR-PROJECT-ID'))

CompV1deployBlock      = 6400278
# If we use 1 week before COMP distribution (June 8, 2020):
#EarlyUserCutoffBlock   = 10228172
# If we use the date of the COMP token announcement (Feb 20, 2020):
#EarlyUserCutoffBlock = 9516777
EarlyUserCutoffBlock = 7900000 # for testing

# ...sort transaction data by address and then by block and token
#txData = txData.sort_values(['address','block','token'])
txData = txData.sort_values(['address','block'])

# Initialize a dataframe to store addresses' interest by token
accruedInterest = txData[['address']]
accruedInterest = pd.DataFrame(accruedInterest['address'].unique(),columns=['address'])
cTokenContract = []
for token in cTokens:
    #with open(token['abi']) as json_file:
    #    cTokenABI = json.load(json_file)
    #    cTokenAddress = token['address']
    #    cTokenContract[token] = w3.eth.contract(cTokenAddress,abi=cTokenABI)
    label = token['abi'].split('.')[0].split('c')[1]
    tokenSupplyExchRate = label + 'SupplyExchRate'
    tokenSupplyInterest = label + 'SupplyInterest'
    tokenSupplyBalance  = label + 'SupplyBalance'
    tokenBorrowExchRate = label + 'BorrowExchRate'
    tokenBorrowInterest = label + 'BorrowInterest'
    tokenBorrowBalance  = label + 'BorrowBalance'
    accruedInterest[tokenSupplyExchRate] = 1
    accruedInterest[tokenSupplyInterest] = 0
    accruedInterest[tokenSupplyBalance] = 0
    accruedInterest[tokenBorrowExchRate] = 1
    accruedInterest[tokenBorrowInterest] = 0
    accruedInterest[tokenBorrowBalance] = 0

# V2 interest accrual is based on cToken exchange rates; so,
# Accrue interest only on withdraw or repay,
# except for a final tally of interest on open supply/borrows
# at the early user cutoff block

block = 0
cToken = 'c'
exchangeRateOld = 0
#lastrow = txData.iloc[0]
for index, row in txData.iterrows():
    #print(row)
    if row['action'] == 'liquidate':
        # Eventually we'll need to bump back one tx and repeat...
        continue
    # Get cToken exchange rate and price of underlying at this block via API call
    elif block != row['block'] or cToken != 'c'+str(row['token']):
        cTokenAmt = int(row['ctokenamt'])
        block = int(row['block'] )
        address = str(row['address'])
        amount = int((row['amount']))
        token = str(row['token'])
        cToken = 'c'+token
        cTokenAddress = get_cToken_address(cToken)
        #response = requests.get('https://api.compound.finance/api/v2/ctoken/?addresses='+cTokenAddress+'&block_number='+str(block))
        #data = json.loads(response.text)
        # NEED TO MOVE DEFN OF tokenSupplyExchRate etc into this LOOP!
        tokenSupplyExchRate = token + 'SupplyExchRate'
        tokenSupplyInterest = token + 'SupplyInterest'
        tokenSupplyBalance  = token + 'SupplyBalance'
        tokenBorrowExchRate = token + 'BorrowExchRate'
        tokenBorrowInterest = token + 'BorrowInterest'
        tokenBorrowBalance  = token + 'BorrowBalance'
        exchangeRateNew  = amount/cTokenAmt
        #exchangeRateNew = float(data['cToken'][0]['exchange_rate']['value'])
        #exchangeRateOld = accruedInterest.loc[accruedInterest['address'] == address,
        #                                  tokenSupplyExchRate]
        #if exchangeRateOld != 0:
        #    exchangeRateOld = float(lastdata['cToken'][0]['exchange_rate']['value'])
        #else:
        #    exchangeRateOld = exchangeRateNew
        #ethPrice = data['cToken'][0]['underlying_price']['value']
    if row['action'] == 'supply':
        exchangeRateOld  = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate].values[0]
        SupplyBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance].values[0]
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate] = exchangeRateNew
        #interest = newBalance - startingBalance - amount
        #print("new - start - amt = int " + str(newBalance) + " " + str(startingBalance) + " " + str(amount) + " " + str(interest))
        #interest = (newBalance - amount)*(exchangeRateNew/(exchangeRateNew+exchangeRateOld))
        interest = SupplyBalanceOld*(exchangeRateNew/exchangeRateOld-1.)
        SupplyBalanceNew = SupplyBalanceOld + interest + amount
        print(SupplyBalanceNew)
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interest 
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance] = SupplyBalanceNew
    elif row['action'] == 'withdraw':
        exchangeRateOld  = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate].values[0]
        SupplyBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance].values[0]
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate] = exchangeRateNew
        #try:
        #    startingBalance = int(accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance])
        #except:
        #    startingBalance = 0
        #interest = newBalance - startingBalance + amount
        #print("Redeem: new - start + amt = int " + str(newBalance) + " " + str(startingBalance) + " " + str(amount) + " " + str(interest))
        #interest = (newBalance + amount)*(exchangeRateNew/(exchangeRateNew+exchangeRateOld))
        interest = SupplyBalanceOld*(exchangeRateNew/exchangeRateOld-1.)
        SupplyBalanceNew = SupplyBalanceOld + interest - amount
        print(SupplyBalanceOld)
        print(interest)
        print(amount)
        print(SupplyBalanceNew)
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interest 
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance] = SupplyBalanceNew
    elif row['action'] == 'borrow':
        exchangeRateOld  = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowExchRate].values[0]
        BorrowBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance].values[0]
        accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowExchRate] = exchangeRateNew
        #try:
        #    startingBalance = int(accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance])
        #except:
        #    startingBalance = 0
        #interest = newBalance - startingBalance - amount
        #print("Borrow: new - start - amt = int " + str(newBalance) + " " + str(startingBalance) + " " + str(amount) + " " + str(interest))
        #interest = (newBalance - amount)*(exchangeRateNew/(exchangeRateNew+exchangeRateOld))
        #interest = BorrowBalanceOld*(1.-exchangeRateNew/exchangeRateOld) - amount
        interest = BorrowBalanceOld*(exchangeRateNew/exchangeRateOld-1.)
        BorrowBalanceNew = BorrowBalanceOld + interest + amount
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenBorrowInterest] += interest 
        accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance] = BorrowBalanceNew
    elif row['action'] == 'repay':
        exchangeRateOld  = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowExchRate].values[0]
        BorrowBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance].values[0]
        accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowExchRate] = exchangeRateNew
        #try:
        #    startingBalance = int(accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance])
        #except:
        #    startingBalance = 0
        #interest = newBalance - startingBalance + amount
        #print("Repay: new - start + amt = int " + str(newBalance) + " " + str(startingBalance) + " " + str(amount) + " " + str(interest))
        #interest = (newBalance + amount)*(exchangeRateNew/(exchangeRateNew+exchangeRateOld))
        interest = BorrowBalanceOld*(1.-exchangeRateNew/exchangeRateOld) - amount
        newBalance = BorrowBalanceOld + amount + interest
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenBorrowInterest] += interest 
        accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance] = newBalance
    #lastdata = data
    #lastrow = row
    print("Accrued " + str(interest*10**(-row['decimals'])) + ' ' + str(token) + " interest to address " + str(address))

#print("Accruing outstanding interest...")
print("Skipping outstanding interest...")
#for index,row in accruedInterest.iterrows():
#    # For each address, find any nonzero final newBalances in the txData
#    thisAddressTxData = txData[txData['address']==row['address']]
#    for token in tokenList:
#        thisTokenTxData = thisAddressTxData[thisAddressTxData['token']==token]
#        try:
#            lastNewBalance = int(thisTokenTxData.tail(1)['newBalance'].values)
#        except:
#            lastNewBalance = int(0)
#        if lastNewBalance != 0:
#            # compute interest on outstanding balance
#            # from blockDelta to last supply/borrow
#            # and interest rate per block at EarlyUserCutoffBlock
#            lastTxBlock = thisTokenTxData.tail(1)['block'].values[0]
#            blockDelta = int(EarlyUserCutoffBlock - lastTxBlock)
#            if (blockDelta < 0):
#                continue
#            thisAction = thisTokenTxData.tail(1)['action'].values
#            for i in range(len(cTokenList)):
#                if cTokenList[i]['label'] == token:
#                    thisToken = cTokenList[i]
#            if thisAction == 'supply' or 'withdraw':
#            # This is the current V2 rate; I don't see a way to
#            # extract the rate at a specific block in the past
#                supplyData = MoneyMarket.functions.markets(thisToken['address']).call()
#                # supplyIndex, Mantissa are 5th, 4th index returned by V1 markets()
#                supplyIndex = float(supplyData[5])
#                supplyRateMantissa = float(supplyData[4])
#                newInterestIndex = (1.+supplyRateMantissa*10**(-thisToken['decimals'])*blockDelta)*supplyIndex
#                newBalance = lastNewBalance*(newInterestIndex/supplyIndex)
#                interest = newBalance - lastNewBalance
#                print('reconciling ' + str(interest) + ' ' + thisToken['label'] + ' to ' + row['address'])
#                #print(row['address'] + " has " + str(newBalance*10**(-thisToken['decimals'])) + " " + thisToken['label'] + " with residual supply interest of " + str(interest*10**(-thisToken['decimals'])) + " " + thisToken['label'])
#                accruedInterest.loc[accruedInterest['address'] == address,
#                                    tokenSupplyInterest] += interest 
#                #print("Accrued supply interest " + str(interest) + " to " + str(row['address']))
#            elif thisAction == 'borrow' or 'repay':
#                borrowData = MoneyMarket.functions.markets(thisToken['address']).call()
#                # borrowIndex, Mantissa are the 8th, 7th index returned by V1 markets()
#                borrowIndex = float(borrowData[8])
#                borrowRateMantissa = float(borrowData[7])
#                newInterestIndex = (1.+borrowRateMantissa*10**(-thisToken['decimals'])*blockDelta)*borrowIndex
#                newBalance = lastNewBalance*(newInterestIndex/supplyIndex)
#                interest = newBalance - lastNewBalance
#                print('reconciling ' + interest + ' ' + thisToken['label'] + ' to ' + row['address'])
#                #print(row['address'] + " has " + str(newBalance*10**(-thisToken['decimals'])) + " " + thisToken['label'] + " with residual supply interest of " + str(interest*10**(-thisToken['decimals'])) + " " + thisToken['label'])
#                accruedInterest.loc[accruedInterest['address'] == address,
#                                    tokenBorrowInterest] += interest 
#                #print("Accrued borrow (repay) interest " + str(interest) + " to " + str(row['address']))
#            # We should technically step back recursively to last non-liquidate
#            # action if user's last action was a liquidation; this is on the to-do list 
#
accruedInterest.to_csv(outfile)
