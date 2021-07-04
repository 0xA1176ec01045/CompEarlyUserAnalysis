import pandas as pd
import web3
import json
import requests
from datetime import date
from sys import argv

earlyUserFile = 'CompoundV2.EarlyUserEvents.csv'
outfile = 'CompoundV2.EarlyUserUSDInterest.csv'
txData = pd.read_csv(earlyUserFile)

tokenList = ['ZRX','BAT','REP','WETH','SAI','ETH','USDC','WBTC','DAI']

# cToken contract metadata
# Only includes contracts deployed before block 9601359 (release of COMP)
cZRX = {
  "address"     : '0xB3319f5D18Bc0D84dD1b4825Dcde5d5f7266d407',
  "deployBlock" : 7710735,
  "abi"         : 'cZRX.abi.json',
  "decUnder"    : 18
}
cBAT = {
  "address"     : '0x6C8c6b02E7b2BE14d4fA6022Dfd6d75921D90E4E',
  "deployBlock" : 7710735,
  "abi"         : 'cBAT.abi.json',
  "decUnder"    : 18
}
cSAI = {
  "address"     : '0xF5DCe57282A584D2746FaF1593d3121Fcac444dC',
  "deployBlock" : 7710752,
  "abi"         : 'cSAI.abi.json',
  "decUnder"    : 18
}
cREP = {
  "address"     : '0x158079Ee67Fce2f58472A96584A73C7Ab9AC95c1',
  "deployBlock" : 7710755,
  "abi"         : 'cREP.abi.json',
  "decUnder"    : 18
}
cETH = {
  "address"     : '0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5',
  "deployBlock" : 7710758,
  "abi"         : 'cETH.abi.json',
  "decUnder"    : 18
}
cUSDC = {
  "address"     : '0x39AA39c021dfbaE8faC545936693aC917d5E7563',
  "deployBlock" : 7710760,
  "abi"         : 'cUSDC.abi.json',
  "decUnder"    : 6
}
cWBTC = {
  "address"     : '0xC11b1268C1A384e55C48c2391d8d480264A3A7F4',
  "deployBlock" : 8163813,
  "abi"         : 'cWBTC.abi.json',
  "decUnder"    : 8
}
cDAI = {
  "address"     : '0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643',
  "deployBlock" : 8983575,
  "abi"         : 'cDAI.abi.json',
  "decUnder"    : 18
}
cTokens = [cZRX,cBAT,cSAI,cREP,cETH,cUSDC,cWBTC,cDAI]
cTokenDecimals = 8

def get_cToken_address(cToken):
    '''Return the address associated with the specified cToken'''
    for token in cTokens:
        if cToken == token['abi'].split('.')[0]:
            return token['address']
    return '0x'

def getClosestAvailableBlock(targetBlock,historicalData):
    '''Figure out which block within the historical data
       is closest to the target block.
       historyBlocks is the list of buckets by block from
       the Compound MarketHistory API'''
    # Figure out where targetBlock sits in the list of blocks in dataset
    closestBlock = 0
    smallestBlockDelta = 1e6
    for block in historicalData:
       blockDelta = targetBlock - block
       if abs(blockDelta) < abs(smallestBlockDelta):           
           smallestBlockDelta = blockDelta
           closestBlock = block
    return int(closestBlock)
    
CoinGeckoLabel = {'ZRX' : '0x',
                  'BAT' : 'basic-attention-token',
                  'REP' : 'augur',
                  'WETH': 'ethereum', # use ethereum records for WETH price (CoinGecko weth has holes)
                  'SAI' : 'sai',
                  'ETH' : 'ethereum',
                  'USDC': 'usd-coin',
                  'WBTC': 'wrapped-bitcoin',
                  'DAI' : 'dai'
                 }

# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
w3 = web3.Web3(web3.Web3.HTTPProvider('YOUR-RPC-HERE'))
CompV1deployBlock      = 6400278
# Cutoff at date of COMP token announcement:
# Using first block found on Feb 26, 2020 UTC:
EarlyUserCutoffBlock = 9555731
# Average number of blocks per year, for translating APR to rate per block
avgSecondsPerBlock = 13.
blocksPerYear = 365.25*24.*60.*60./13.

# Concatenate transfer data with contract interaction data
transferData = pd.read_csv('CompoundV2.EarlyUserTransfers.csv')
#transferData = pd.read_csv('test0x3Transfers.csv')
txData = pd.concat([txData,transferData], axis=0, ignore_index=True)
for index, row in txData.iterrows():
    if row['action'] == 'transfer':
        txData.loc[index, 'address'] = row['receiver']
    else:
        txData.loc[index, 'sender'] = row['address']
        txData.loc[index, 'receiver'] = row['address']

# ...sort transaction data by block
txData = txData.sort_values(['block'])

# ... exclude any transactions in the event log that took place after EarlyUserCutoffBlock
txData = txData[txData['block'] <= EarlyUserCutoffBlock]

# ... go ahead and gather liquidation-specific data
liqData = pd.read_csv('CompoundV2.EarlyUserEvents.liq.csv',header=None,skiprows=1,
            names=['block','txhash','liquidator','action','token','decimals',
                   'amount','seizeTokens','borrower'])

# Initialize a dataframe to store addresses' interest by token
accruedInterest = txData[['address']]
accruedInterest = pd.DataFrame(accruedInterest['address'].unique(),columns=['address'])
cTokenContract = []
for token in cTokens:
    label = token['abi'].split('.')[0].split('c')[1]
    tokenSupplyExchRate = label + 'SupplyExchRate'
    tokenSupplyInterest = label + 'SupplyInterest'
    tokenSupplyBalance  = label + 'SupplyBalance'
    tokenBorrowInterest = label + 'BorrowInterest'
    tokenBorrowBalance  = label + 'BorrowBalance'
    accruedInterest[tokenSupplyExchRate] = 0.02
    accruedInterest[tokenSupplyInterest] = 0.
    accruedInterest[tokenSupplyBalance] = 0.
    accruedInterest[tokenBorrowInterest] = 0.
    accruedInterest[tokenBorrowBalance] = 0.

# Pull historical price data from CoinGecko API into a dataframe 'pricedata'
pricedata = dict()
startTimeStamp = w3.eth.getBlock(CompV1deployBlock)['timestamp']
startDate = date.fromtimestamp(startTimeStamp)
endTimeStamp   = w3.eth.getBlock(EarlyUserCutoffBlock)['timestamp']
endDate = date.fromtimestamp(endTimeStamp)
daysToQuery = str((date.today()-startDate).days)
datelist = pd.date_range(startDate,endDate).tolist()
for token in tokenList:
    pricedata[token] = dict()
    apicall  = 'https://api.coingecko.com/api/v3/coins/'+CoinGeckoLabel[token]
    apicall += '/market_chart?vs_currency=usd&days='+daysToQuery+'&interval=daily'
    response = requests.get(apicall)
    apidata = json.loads(response.content)
    i = 0 
    for day in datelist:
        try:
            pricedata[token][day.toordinal()] = apidata['prices'][i][1]
        except:
            pricedata[token][day.toordinal()] = 0.
        i += 1

# Gather market history data needed for initial and outstanding interest via Compound MarketHistoryService API
exchangeRates = dict()
borrowRates = dict()
historyBuckets = dict()
startTimeStamp = w3.eth.getBlock(CompV1deployBlock)['timestamp']
startDate = date.fromtimestamp(startTimeStamp)
endTimeStamp   = w3.eth.getBlock(EarlyUserCutoffBlock)['timestamp']
endDate = date.fromtimestamp(endTimeStamp)
EarlyUserCutoffDay = endDate.day
daysToQuery = str((endDate-startDate).days)
for token in cTokens:
    label = token['abi'].split('.')[0].split('c')[1]
    exchangeRates[label] = dict()
    borrowRates[label] = dict()
    address = token['address']
    apicall = 'https://api.compound.finance/api/v2/market_history/graph?asset='
    apicall += str(address)+'&min_block_timestamp='+str(startTimeStamp)
    apicall +='&max_block_timestamp='+str(endTimeStamp)+'&num_buckets='+daysToQuery
    response = requests.get(apicall)
    apidata = json.loads(response.content)
    for i in range(len(apidata['exchange_rates'])):
        block = apidata['exchange_rates'][i]['block_number']
        exchangeRates[label][block] = apidata['exchange_rates'][i]['rate']
        borrowRates[label][block] = apidata['borrow_rates'][i]['rate']

# V2 interest accrual is based on cToken exchange rates; so,
# Accrue interest only on withdraw or repay,
# except for a final tally of interest on open supply/borrows
# at the early user cutoff block

block = 0
cToken = 'c'
exchangeRateOld = 0
printctr=0
negInterestCtr = 0
for index, row in txData.iterrows():
    if row['block'] > EarlyUserCutoffBlock:
        print("Skipping tx in block " + str(row['block']) + " > EarlyUserCutoffBlock")
        continue
    printctr += 1
    if printctr % 100 == 0:
        print("...on transaction " + str(printctr) + " of " + str(len(txData))) 
    cTokenAmt = float(row['state'])
    txhash = str(row['txhash'])
    block = int(row['block'])
    amount = float(row['amount'])
    token = str(row['token'])
    decimals = int(row['decimals'])
    cToken = 'c'+token
    cTokenAddress = get_cToken_address(cToken)
    tokenSupplyExchRate = token + 'SupplyExchRate'
    tokenSupplyInterest = token + 'SupplyInterest'
    tokenSupplyBalance  = token + 'SupplyBalance'
    tokenBorrowInterest = token + 'BorrowInterest'
    tokenBorrowBalance  = token + 'BorrowBalance'
    # Get timestamp for this block
    blockInfo    = w3.eth.getBlock(block)
    timestamp    = blockInfo['timestamp']
    blockdate    = date.fromtimestamp(timestamp)
    # Get USD conversion factor for this token and date
    print("on address " + str(row['address']) + " and txhash = " + str(txhash[:10]) + '...')
    convertToUSD = pricedata[token][blockdate.toordinal()]*10**(-decimals)
    if row['action'] == 'supply':
        address = str(row['address'])
        if cTokenAmt == 0 or amount == 0:
            # No interest, but will create a div-by-0 error; skip
            print("Skipping zero-interest event")
            continue
        exchangeRateNew  = (amount*10**(-decimals))/(cTokenAmt*10**(-cTokenDecimals))
        exchangeRateOld  = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate].values[0]
        if exchangeRateNew < exchangeRateOld:
            print("Notice:  current exchangeRate is smaller than previous exchangeRate;")
            print("         this can only happen if closestAvailableBlock in API data preceeds")
            print("         that of the previous transaction, which can happen for txs taking")
            print("         place in quick succession.")
            print("         Raising previous exchangeRate to match current exchangeRate (zero interest)")
            exchangeRateOld = exchangeRateNew
        SupplyBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance].values[0]
        interest = SupplyBalanceOld*(exchangeRateNew/exchangeRateOld-1.)
        interestUSD = interest*convertToUSD
        if (interest < 0):
            negInterestCtr += 1
        SupplyBalanceNew = SupplyBalanceOld + interest + amount
        print("supply balance new = " + str(SupplyBalanceNew))
        if SupplyBalanceNew < 0:
            # SupplyBalanceNew can be miscalculated and appear negative if address traded cTokens on secondary markets
            # If this happens, reset the SupplyBalanceNew and interest to zero to prevent accumulation of negative interest
            SupplyBalanceNew = 0
            interest = 0
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interestUSD
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance] = SupplyBalanceNew
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate] = exchangeRateNew
    elif row['action'] == 'withdraw':
        address = str(row['address'])
        if cTokenAmt == 0 or amount == 0:
            # No interest, but will create a div-by-0 error; skip
            print("Skipping zero-interest event")
            continue
        exchangeRateNew  = (amount*10**(-decimals))/(cTokenAmt*10**(-cTokenDecimals))
        print("Check exchangeRateNew calc:")
        print("amount = " + str(amount))
        print("cTokenAmt = " + str(cTokenAmt))
        print("decimals = " + str(decimals))
        print("cTokenDecimals = " + str(cTokenDecimals))
        if abs(exchangeRateNew-0.025) > 0.05:
            print('warning: new exchange rate seems abnormally large')
        exchangeRateOld  = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate].values[0]
        if exchangeRateNew < exchangeRateOld:
            print("Warning: current exchangeRate is smaller than previous exchangeRate;")
            print("         this can only happen if closestAvailableBlock in API data places")
            print("         it earlier than previous transaction (can happen for txs taking")
            print("         place in quick succession).")
            print("         Raising previous exchangeRate to match current exchangeRate (zero interest)")
            exchangeRateOld = exchangeRateNew
        print("accruedInterest check before interest on redeem:")
        print(accruedInterest.loc[accruedInterest['address'] == address])
        SupplyBalanceOld = accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance].values[0]
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate] = exchangeRateNew
        print("SupplyBalanceOld = " + str(SupplyBalanceOld))
        print("exchangeRateOld = " + str(exchangeRateOld))
        print("exchangeRateNew = " + str(exchangeRateNew))
        interest = SupplyBalanceOld*(exchangeRateNew/exchangeRateOld-1.)
        interestUSD = interest*convertToUSD
        print("redeem interest = " + str(interest))
        if (interest < 0):
            negInterestCtr += 1
        SupplyBalanceNew = SupplyBalanceOld + interest - amount
        print("SupplyBalanceNew = " + str(SupplyBalanceNew))
        if SupplyBalanceNew < 0:
            # SupplyBalanceNew can be miscalculated and appear negative if address traded cTokens on secondary markets
            # If this happens, reset the SupplyBalanceNew and interest to zero to prevent accumulation of negative interest
            SupplyBalanceNew = 0
            interest = 0
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interestUSD
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyBalance] = SupplyBalanceNew
        accruedInterest.loc[accruedInterest['address'] == address, tokenSupplyExchRate] = exchangeRateNew
    elif row['action'] == 'borrow':
        address = str(row['address'])
        # For borrow/repay, the state variable cTokenAmt is actually 'accountBorrows' in the cToken contracts,
        # which we call newBalance here to distinguish it from the previous startingBalance
        newBalance = float(cTokenAmt)
        try:
            startingBalance = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance].values[0]
        except:
            startingBalance = 0
        interest = newBalance - startingBalance - amount
        interestUSD = interest*convertToUSD
        if interest < 0:
            negInterestCtr += 1
        else:
            accruedInterest.loc[accruedInterest['address'] == address,
                                tokenBorrowInterest] += interestUSD
        accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance] = newBalance
    elif row['action'] == 'repay':
        address = str(row['address'])
        # For borrow/repay, the state variable cTokenAmt is actually 'accountBorrows' in the cToken contracts,
        # which we call newBalance here to distinguish it from the previous startingBalance
        newBalance = float(cTokenAmt)
        try:
            startingBalance = accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance].values[0]
        except:
            startingBalance = 0
        interest = newBalance - startingBalance + amount
        interestUSD = interest*convertToUSD
        if interest < 0:
            negInterestCtr += 1
        else: 
            accruedInterest.loc[accruedInterest['address'] == address,
                            tokenBorrowInterest] += interestUSD 
        accruedInterest.loc[accruedInterest['address'] == address, tokenBorrowBalance] = newBalance
    elif row['action'] == 'liquidate':
        address = str(row['address'])
        # Transfer balance from borrower to liquidator to keep internal record of borrow balances accurate
        # This step is essential for accurate interest accounting on liquidated and liquidating addresses
        # --> add seizeAmount to liquidator's tokenSupplyBalance 
        # --> remove seizeAmount from borrower's tokenSupplyBalance
        thisLiqData = liqData[liqData['txhash'] == txhash]
        liquidatorAddress = str(thisLiqData['liquidator'])
        borrowerAddress = str(thisLiqData['borrower'])
        accruedInterest.loc[accruedInterest['address'] == borrowerAddress, tokenSupplyBalance] -= amount
        accruedInterest.loc[accruedInterest['address'] == liquidatorAddress, tokenSupplyBalance] += amount
    elif row['action'] == 'transfer':
        # Transfer balance from sender to receiver to keep internal record of supply balances accurate
        sender = str(row['sender'])
        receiver = str(row['receiver'])
        # We need to convert from given number of cTokens to the number of underlying tokens with closest available exchange rate
        cTokenAmt = float(row['amount'])
        closestAvailableBlock = getClosestAvailableBlock(block,exchangeRates[token])
        exchangeRate  = exchangeRates[token][closestAvailableBlock]
        amount = (cTokenAmt*10**(-cTokenDecimals))*exchangeRate/10**(-decimals)
        senderBalance = accruedInterest.loc[accruedInterest['address'] == sender, tokenSupplyBalance]
        # Ensure our records are consistent with sender having sufficient balance to send the specified amount
        try:
            senderLatestBalance = senderBalance.values[0]
            if amount > senderLatestBalance:
                print("Notice:  amount this account transferred exceeds estimated balance.")
                print("         This means that ithe most recent supply balance change occured")
                print("         more recently than closestAvailableBlock; round up balance to match amount")
                accruedInterest.loc[accruedInterest['address'] == sender, tokenSupplyBalance] = amount
        except:
            continue
        accruedInterest.loc[accruedInterest['address'] == sender, tokenSupplyBalance] -= amount
        if receiver not in accruedInterest['address'].values:
            newrow = pd.Series(0.0,accruedInterest.columns)
            newrow['address'] = receiver
            newrow[tokenSupplyBalance] = amount
            newrow[tokenSupplyExchRate] = exchangeRate
            accruedInterest.loc[len(accruedInterest.index)] = newrow
        else:
            accruedInterest.loc[accruedInterest['address'] == receiver, tokenSupplyBalance] += amount
            accruedInterest.loc[accruedInterest['address'] == receiver, tokenSupplyExchRate] = exchangeRate



print("...completed pre-reconciliation interest accrual with " + str(negInterestCtr) + " putatively negative interest events")
print("Accruing outstanding interest...")
printctr=0
for index,row in accruedInterest.iterrows():
    printctr += 1
    if printctr % 100 == 0:
        print("...on account " + str(printctr) + " of " + str(len(accruedInterest))) 
    # For each address, find nonzero supply and borrow balances
    for token in cTokens:
        label = token['abi'].split('.')[0].split('c')[1]
        tokenSupplyExchRate = label + 'SupplyExchRate'
        tokenSupplyInterest = label + 'SupplyInterest'
        tokenSupplyBalance  = label + 'SupplyBalance'
        tokenBorrowInterest = label + 'BorrowInterest'
        tokenBorrowBalance  = label + 'BorrowBalance'
        decimals = token['decUnder']
        # Get USD conversion factor for this token on endDate
        convertToUSD = pricedata[label][endDate.toordinal()]*10**(-decimals)

        # Reconcile supply interest based on tokenSupplyBalance and SupplyExchRate data;
        # ---> requires knowledge of cToken SupplyRate at EarlyUserCutoffBlock
        # ---> computed from ratio of SupplyRate at latest supply/redeem and SupplyRate at EarlyUserCutoffBlock,
        #      obtained from Compound's MarketHistoryService API

        # Reconcile borrow interest based on tokenBorrowBalance and blockDelta to previous borrow/repay tx
        # ---> tokenBorrowBalance is available in the accrueInterest DataFrame
        # ---> computed from a simple average of BorrowRate at latest borrow/repay and BorrowRate at EarlyUserCutoffBlock,
        #      obtained from Compound's MarketHistoryService API

        # Pull historical rate data from Compound API into a dataframe 'marketRates'
        if row[tokenSupplyBalance] > 0:
            print(row[tokenSupplyBalance])
            # Find the last supply/redeem tx block for this (address,token) pair
            thisAddressTxData = txData[txData['address']==row['address']]
            #print(thisAddressTxData)
            thisAddressTxData = thisAddressTxData[thisAddressTxData['block']<=EarlyUserCutoffBlock]
            thisTokenTxData = thisAddressTxData[thisAddressTxData['token']==label]
            print(thisTokenTxData[['block','action']])
            try:
                lastSupplyTxBlock = thisTokenTxData[thisTokenTxData['action']=='supply']['block'].values[-1]
            except:
                lastSupplyTxBlock = 0
            try:
                lastRedeemTxBlock = thisTokenTxData[thisTokenTxData['action']=='withdraw']['block'].values[-1]
            except:
                lastRedeemTxBlock = 0
            lastTxBlock = int(lastSupplyTxBlock) if lastSupplyTxBlock > lastRedeemTxBlock else int(lastRedeemTxBlock)
            if lastTxBlock == 0:
                print("Address " + str(row['address']) + " has only received, not supplied/redeemed, c" + str(label))
                lastTxBlock = thisTokenTxData[thisTokenTxData['action']=='transfer']['block'].values[-1]
            closestAvailableBlock = getClosestAvailableBlock(lastTxBlock,exchangeRates[label])
            exchangeRateOld  = exchangeRates[label][closestAvailableBlock]
            closestAvailableBlock = getClosestAvailableBlock(EarlyUserCutoffBlock,exchangeRates[label])
            exchangeRateNew  = exchangeRates[label][closestAvailableBlock]
            if exchangeRateNew < exchangeRateOld:
                print("Warning: approximate exchangeRate is smaller than previous exchangeRate;")
                print("         this can only happen if closestAvailableBlock in API data places")
                print("         it earlier than previous transaction (can happen for txs taking")
                print("         place in quick succession).")
                print("         Raising exchangeRate to match previous exchangeRate (zero interest)")
                exchangeRateNew = exchangeRateOld
            SupplyBalanceOld = row[tokenSupplyBalance]
            interest = SupplyBalanceOld*(exchangeRateNew/exchangeRateOld-1.)
            interestUSD = interest*convertToUSD
            accruedInterest.loc[accruedInterest['address'] == row['address'],
                                tokenSupplyInterest] += interestUSD
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
            borrowBalanceOld = row[tokenBorrowBalance]
            # Using two-point approximate average borrow rate
            borrowRateOld = borrowRates[label][closestAvailableBlock]
            closestAvailableBlock = getClosestAvailableBlock(EarlyUserCutoffBlock,borrowRates[label])
            borrowRateNew = borrowRates[label][closestAvailableBlock]
            # Take average and convert from annual rate to per-block rate
            borrowRateAvg = 0.5*(borrowRateOld+borrowRateNew)/blocksPerYear
            interest = borrowBalanceOld*borrowRateAvg*blockDelta
            interestUSD = interest*convertToUSD
            accruedInterest.loc[accruedInterest['address'] == row['address'],
                                tokenBorrowInterest] += interestUSD 

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
simplifiedInterest.to_csv(outfile,index=False)
