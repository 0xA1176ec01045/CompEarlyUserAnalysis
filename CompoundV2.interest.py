import pandas as pd
import web3
import json
import requests
from datetime import date
from sys import argv

earlyUserFile = 'trouble2.csv'
outfile = 'CompoundV2.EarlyUserInterest.csv'
txData = pd.read_csv(earlyUserFile,
            names=['block','txhash','address','action','token','decimals',
                   'amount','ctokenamt'])
#txData = pd.read_csv(earlyUserFile)

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

def getClosestAvailableBlock(targetBlock,historicalData):
    '''Figure out which block within the historical data
       is closest to the target block.
       historyBlocks is the list of buckets by block from
       the Compound MarketHistory API'''
    # Figure out where targetDay sits in the list of dates in dataset
    closestBlock = 0
    smallestBlockDelta = 1e6
    #print(historicalData)
    for block in historicalData:
       blockDelta = targetBlock - block
       if abs(blockDelta) < abs(smallestBlockDelta):           
           smallestBlockDelta = blockDelta
           closestBlock = block
    return int(closestBlock)
    
# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
w3 = web3.Web3(web3.Web3.HTTPProvider('YOUR-NODE-HERE'))

CompV1deployBlock      = 6400278
# If we use 1 week before COMP distribution (June 8, 2020):
#EarlyUserCutoffBlock   = 10228172
# If we use the date of the COMP token announcement (Feb 20, 2020):
EarlyUserCutoffBlock = 9516777
#EarlyUserCutoffBlock = 7900000 # for testing
# Average number of blocks per year, for translating APR to rate per block
avgSecondsPerBlock = 13.
blocksPerYear = 365.25*24.*60.*60./13.

# ...sort transaction data by address and then by block and token
#txData = txData.sort_values(['address','block','token'])
#txData = txData.sort_values(['address','block'])

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
    #tokenBorrowExchRate = label + 'BorrowExchRate'
    tokenBorrowInterest = label + 'BorrowInterest'
    tokenBorrowBalance  = label + 'BorrowBalance'
    accruedInterest[tokenSupplyExchRate] = 1.
    accruedInterest[tokenSupplyInterest] = 0.
    accruedInterest[tokenSupplyBalance] = 0.
    #accruedInterest[tokenBorrowExchRate] = 1.
    accruedInterest[tokenBorrowInterest] = 0.
    accruedInterest[tokenBorrowBalance] = 0.

# V2 interest accrual is based on cToken exchange rates; so,
# Accrue interest only on withdraw or repay,
# except for a final tally of interest on open supply/borrows
# at the early user cutoff block

block = 0
cToken = 'c'
exchangeRateOld = 0
#lastrow = txData.iloc[0]
printctr=0
for index, row in txData.iterrows():
    if row['block'] > EarlyUserCutoffBlock:
        continue
    printctr += 1
    if printctr % 100 == 0:
        print("...on transaction " + str(printctr) + " of " + str(len(txData))) 
    if row['action'] == 'liquidate':
        # Eventually we'll need to bump back one tx and repeat...
        continue
    # Get cToken exchange rate and price of underlying at this block via API call
    elif block != row['block'] or cToken != 'c'+str(row['token']):
        cTokenAmt = float(row['ctokenamt'])
        #print(cTokenAmt)
        block = float(row['block'] )
        address = str(row['address'])
        amount = float((row['amount']))
        token = str(row['token'])
        cToken = 'c'+token
        cTokenAddress = get_cToken_address(cToken)
        tokenSupplyExchRate = token + 'SupplyExchRate'
        tokenSupplyInterest = token + 'SupplyInterest'
        tokenSupplyBalance  = token + 'SupplyBalance'
        #tokenBorrowExchRate = token + 'BorrowExchRate'
        tokenBorrowInterest = token + 'BorrowInterest'
        tokenBorrowBalance  = token + 'BorrowBalance'
        #exchangeRateNew = float(data['cToken'][0]['exchange_rate']['value'])
        #exchangeRateOld = accruedInterest.loc[accruedInterest['address'] == address,
        #                                  tokenSupplyExchRate]
        #if exchangeRateOld != 0:
        #    exchangeRateOld = float(lastdata['cToken'][0]['exchange_rate']['value'])
        #else:
        #    exchangeRateOld = exchangeRateNew
        #ethPrice = data['cToken'][0]['underlying_price']['value']
    if row['action'] == 'supply':
        if cTokenAmt == 0:
            # Too small to accrue any interest, but will create a div-by-0 error; skip it
            continue
        exchangeRateNew  = amount/cTokenAmt
        exchangeRateOld  = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate].values[0]
        SupplyBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance].values[0]
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate] = exchangeRateNew
        #interest = newBalance - startingBalance - amount
        #print("new - start - amt = int " + str(newBalance) + " " + str(startingBalance) + " " + str(amount) + " " + str(interest))
        #interest = (newBalance - amount)*(exchangeRateNew/(exchangeRateNew+exchangeRateOld))
        interest = SupplyBalanceOld*(exchangeRateNew/exchangeRateOld-1.)
        SupplyBalanceNew = SupplyBalanceOld + interest + amount
        #print(address, SupplyBalanceNew)
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interest 
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance] = SupplyBalanceNew
    elif row['action'] == 'withdraw':
            # Too small to accrue any interest, but will create a div-by-0 error; skip it
        if cTokenAmt == 0:
            continue
        exchangeRateNew  = amount/cTokenAmt
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
        #print(SupplyBalanceOld)
        #print(interest)
        #print(amount)
        #print(SupplyBalanceNew)
        #print(address, SupplyBalanceNew)
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interest 
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance] = SupplyBalanceNew
    elif row['action'] == 'borrow':
        # For borrow/repay, cTokenAmt is actually accountBorrows, which is newBorrowBalance
        #exchangeRateOld  = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowExchRate].values[0]
        #BorrowBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance].values[0]
        #accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowExchRate] = exchangeRateNew
        newBalance = float(cTokenAmt)
        #print(address,newBalance)
        try:
            startingBalance = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance].values[0]
        except:
            startingBalance = 0
        interest = newBalance - startingBalance - amount
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenBorrowInterest] += interest 
        accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance] = newBalance
    elif row['action'] == 'repay':
        # For borrow/repay, cTokenAmt is actually accountBorrows, which is newBorrowBalance
        newBalance = float(cTokenAmt)
        #print(newBalance)
        try:
            startingBalance = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance].values[0]
        except:
            startingBalance = 0
        interest = newBalance - startingBalance + amount
        #print("Repay: new - start + amt = int " + str(newBalance) + " " + str(startingBalance) + " " + str(amount) + " " + str(interest))
        #interest = (newBalance + amount)*(exchangeRateNew/(exchangeRateNew+exchangeRateOld))
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenBorrowInterest] += interest 
        accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance] = newBalance
    print("...Accrued " + str(interest*10**(-row['decimals'])) + ' ' + str(token) + " interest to address " + str(address))

#print("Skipping outstanding interest...")

# Gather market history data needed for outstanding interest via Compound MarketHistoryService API
supplyRates = dict()
borrowRates = dict()
historyBuckets = dict()
startTimeStamp = w3.eth.getBlock(CompV1deployBlock)['timestamp']
startDate = date.fromtimestamp(startTimeStamp)
endTimeStamp   = w3.eth.getBlock(EarlyUserCutoffBlock)['timestamp']
endDate = date.fromtimestamp(endTimeStamp)
EarlyUserCutoffDay = endDate.day
daysToQuery = str((endDate-startDate).days)
#datelist = pd.date_range(startDate,endDate).tolist()
for token in cTokens:
    label = token['abi'].split('.')[0].split('c')[1]
    #print(label)
    supplyRates[label] = dict()
    borrowRates[label] = dict()
    address = token['address']
    apicall = 'https://api.compound.finance/api/v2/market_history/graph?asset='
    apicall += str(address)+'&min_block_timestamp='+str(startTimeStamp)
    apicall +='&max_block_timestamp='+str(endTimeStamp)+'&num_buckets='+daysToQuery
    #print(apicall)
    response = requests.get(apicall)
    apidata = json.loads(response.content)
    for i in range(len(apidata['supply_rates'])):
        block = apidata['supply_rates'][i]['block_number']
        supplyRates[label][block] = apidata['supply_rates'][i]['rate']
        borrowRates[label][block] = apidata['borrow_rates'][i]['rate']
    #print("Checking supplyRates and borrowRates for " + label)
    #print(supplyRates[label])
    #print(borrowRates[label])

print("Accruing outstanding interest...")
for index,row in accruedInterest.iterrows():
    # For each address, find nonzero supply and borrow balances
    for token in cTokens:
        label = token['abi'].split('.')[0].split('c')[1]
        tokenSupplyExchRate = label + 'SupplyExchRate'
        tokenSupplyInterest = label + 'SupplyInterest'
        tokenSupplyBalance  = label + 'SupplyBalance'
        tokenBorrowInterest = label + 'BorrowInterest'
        tokenBorrowBalance  = label + 'BorrowBalance'
        print("Inspecting " + label)

        # Reconcile supply interest based on tokenSupplyBalance and SupplyExchRate data;
        # ---> requires knowledge of cToken SupplyExchRate at EarlyUserCutoffBlock
        # ---> Let's take a simple average of SupplyRate at latest supply/redeem and SupplyRate at EarlyUserCutoffBlock,
        #      obtained from Compound's MarketHistoryService API
        #      ... possible improvement: use average SupplyRate over the entire blockDelta, subdivided into narrow bins

        # Reconcile borrow interest based on tokenBorrowBalance and blockDelta to previous borrow/repay tx
        # ---> tokenBorrowBalance is available in the accrueInterest DataFrame
        # ---> Let's take a simple average of BorrowRate at latest borrow/repay and BorrowRate at EarlyUserCutoffBlock,
        #      obtained from Compound's MarketHistoryService API

        # (3) Perform the interest calculations, interest = Balance*avgRatePerBlock*blockDelta

# Pull historical rate data from Compound API into a dataframe 'marketRates'

        # Scan accruedInterest for non-zero SupplyBalance, BorrowBalance
        if row[tokenSupplyBalance] > 0:
            # Find the last supply/redeem tx block for this (address,token) pair
            thisAddressTxData = txData[txData['address']==row['address']]
            thisTokenTxData = thisAddressTxData[thisAddressTxData['token']==label]
            try:
                lastSupplyTxBlock = thisTokenTxData[thisTokenTxData['action']=='supply']['block'].values[-1]
            except:
                lastSupplyTxBlock = 0
            try:
                lastRedeemTxBlock = thisTokenTxData[thisTokenTxData['action']=='redeem']['block'].values[-1]
            except:
                lastRedeemTxBlock = 0
            lastTxBlock = int(lastSupplyTxBlock) if lastSupplyTxBlock > lastRedeemTxBlock else int(lastRedeemTxBlock)
            #print(lastTxBlock)
            closestAvailableBlock = getClosestAvailableBlock(lastTxBlock,supplyRates[label])
            #print("Closest available block to last tx = " + str(closestAvailableBlock))
            ### I should be grabbing EXCHANGE RATES here, not SUPPLY RATES!
            exchangeRateOld  = supplyRates[label][closestAvailableBlock]
            closestAvailableBlock = getClosestAvailableBlock(EarlyUserCutoffBlock,supplyRates[label])
            #print(EarlyUserCutoffBlock)
            #print("Closest available block to EarlyUserCutoff = " + str(closestAvailableBlock))
            exchangeRateNew  = supplyRates[label][closestAvailableBlock]
            SupplyBalanceOld = row[tokenSupplyBalance]
            # The try-except below should give identical results, but isn't;
            # this inconsistency ought to be resolved
            #try:
            #    SupplyBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance].values[0]
            #except:
            #    SupplyBalanceOld = 0
            interest = SupplyBalanceOld*(exchangeRateNew/exchangeRateOld-1.)
            print("Reconciling " + str(interest) + " outstanding " + label + " supply interest to " + address)
            print("Diagnostics: SupplyBalance = " + str(SupplyBalanceOld))
            accruedInterest.loc[accruedInterest['address'] == address,
                                tokenSupplyInterest] += interest 
        if row[tokenBorrowBalance] > 0:
            # Find the last borrow/repay tx block for this (address,token) pair
            thisAddressTxData = txData[txData['address']==row['address']]
            thisTokenTxData = thisAddressTxData[thisAddressTxData['token']==label]
            try:
                lastBorrowTxBlock = thisTokenTxData[thisTokenTxData['action']=='borrow']['block'].values[-1]
            except:
                lastBorrowTxBlock = 0
            try:
                lastRepayTxBlock = thisTokenTxData[thisTokenTxData['action']=='repay']['block'].values[-1]
            except:
                lastRepayTxBlock = 0
            lastTxBlock = int(lastBorrowTxBlock) if lastBorrowTxBlock > lastRepayTxBlock else int(lastRepayTxBlock)
            closestAvailableBlock = getClosestAvailableBlock(lastTxBlock,borrowRates[label])
            blockDelta = int(EarlyUserCutoffBlock - lastTxBlock)
            #try:
            #borrowBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance].values[0]
            #except:
            #    borrowBalanceOld = 0
            borrowBalanceOld = row[tokenBorrowBalance]
            # Using two-point approximate average borrow rate
            borrowRateOld = borrowRates[label][closestAvailableBlock]
            closestAvailableBlock = getClosestAvailableBlock(EarlyUserCutoffBlock,borrowRates[label])
            borrowRateNew = borrowRates[label][closestAvailableBlock]
            # Take average and convert from annual rate to per-block rate
            borrowRateAvg = 0.5*(borrowRateOld+borrowRateNew)/blocksPerYear
            interest = borrowBalanceOld*borrowRateAvg*blockDelta
            print("Reconciling " + str(interest) + " outstanding " + label + " borrow interest to " + address)
            print("Diagnostics: borrowBalance = " + str(borrowBalanceOld))
            accruedInterest.loc[accruedInterest['address'] == address,
                                tokenBorrowInterest] += interest 

#accruedInterest.to_csv(outfile)
dropCols = []
for token in cTokens:
    label = token['abi'].split('.')[0].split('c')[1]
    tokenSupplyExchRate = label + 'SupplyExchRate'
    tokenSupplyBalance  = label + 'SupplyBalance'
    tokenBorrowBalance  = label + 'BorrowBalance'
    dropCols.append(tokenSupplyExchRate)
    dropCols.append(tokenSupplyBalance)
    dropCols.append(tokenBorrowBalance)
simplifiedInterest = accruedInterest.drop(columns=dropCols)
simplifiedInterest.to_csv(outfile)
