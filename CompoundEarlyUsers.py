import web3
import json
from time import sleep

batchSize = 100       # size of each batch of blocks;
                      # we use this to sidestep potential limits
                      # on number of events returned by getLogs()

CompoundV1Outfile = 'CompoundV1.EarlyUserEvents.csv'
CompoundV2Outfile = 'CompoundV2.EarlyUserEvents.csv'
CompoundV1LiqOutfile = 'CompoundV1.EarlyUserEvents.liq.csv'
CompoundV2LiqOutfile = 'CompoundV2.EarlyUserEvents.liq.csv'
CompoundV2TransferOutfile = 'CompoundV2.EarlyUserTransfers.csv'

# Compound V1 contract metadata
CompV1 = {
  "address"     : '0x3FDA67f7583380E67ef93072294a7fAc882FD7E7',
  "deployBlock" : 6400278,
  "abi"         : 'CompoundV1.abi.json'
}
ZRX = {
  "address"     : '0xE41d2489571d322189246DaFA5ebDe1F4699F498',
  "label"       : 'ZRX',
  "decimals"    : 18
}
BAT = {
  "address"     : '0x0D8775F648430679A709E98d2b0Cb6250d2887EF',
  "label"       : 'BAT',
  "decimals"     : 18
}
REP = {
  "address"     : '0x1985365e9f78359a9B6AD760e32412f4a445E862',
  "label"       : 'REP',
  "decimals"    : 18
}
WETH = {
  "address"     : '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
  "label"       : 'WETH',
  "decimals"    : 18
}
SAI = {
  "address"     : '0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359',
  "label"       : 'SAI',
  "decimals"    : 18
}
V1Tokens = [ZRX,BAT,REP,WETH,SAI]

# cToken contract metadata
# Only includes contracts deployed before release of COMP
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

# Finally we also need decimals of the underlying tokens that weren't in V1
USDC = {
  "address"     : '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
  "decimals"    : 6
}
WBTC = {
  "address"     : '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',
  "decimals"    : 8
}
DAI = {
  "address"     : '0x6b175474e89094c44da98b954eedeac495271d0f',
  "decimals"    : 18
}
ETH = {
  "decimals"    : 18
}

actions = ["supply","withdraw","borrow","repay","liquidate"]

# No need to review blocks prior to first cToken deployment (cZRX);
# No need to review blocks after COMP launch June 16, 2020.
# Last block produced on June 15, 2020 is 10273464

# Early users are defined here as those who tested the protocol
# by interacting with it on mainnet before the COMP token and
# distribution were announced on Feb 26, 2020;
#     EarlyUserCutoffBlock is first block Feb 26, 2020 UTC
CompV1deployBlock      = CompV1["deployBlock"]
cZRXdeployBlock        = cZRX["deployBlock"]
COMPdeployBlock        = 9601359
EarlyUserCutoffBlock   = 9555731

# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
# --> User must provide a valid Infura Project ID or replace with a local ethereum IPC 
w3 = web3.Web3(web3.Web3.HTTPProvider('https://dry-empty-sunset.quiknode.io/36e947d3-a37c-4480-a42a-8a879acbcf51/Lr6bbYqSl6kFkTRn5TG_OY3KOs13qPq0H-pKUtjqiu2XP-YOeyTdTKhb5Z56dQgFQb49acVpR5olMxSuLVznmg==/'))

# Gather Compound V1 Early User Interactions
# Open ABI and gather events for the V1 contract
with open('abis/'+CompV1["abi"]) as json_file:
    CompoundV1ABI = json.load(json_file)
    MoneyMarketABI = CompoundV1ABI["MoneyMarket"]
outfile = open(CompoundV1Outfile,'w')
outfile.write("block,txhash,address,action,token,decimals,amount,startingBalance,newBalance")
liqOutfile = open(CompoundV1LiqOutfile,'w')
liqOutfile.write("block,txhash,address,action,token,decimals,amount,startingBalance,newBalance")

CompV1["contract"] = w3.eth.contract(CompV1["address"],abi=MoneyMarketABI)
print("Opening V1 contract...")
for batch in range(CompV1deployBlock,EarlyUserCutoffBlock,batchSize):
    startBlock = batch
    endBlock = batch+batchSize-1
    print("Collecting logs for batch from " + str(startBlock) + " to " + str(endBlock))
    if endBlock > EarlyUserCutoffBlock:
        endBlock = EarlyUserCutoffBlock
    print("...pulling supplies")
    CompV1["supply"]    = CompV1["contract"].events.SupplyReceived.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    print("...pulling withdrawals")
    CompV1["withdraw"]  = CompV1["contract"].events.SupplyWithdrawn.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    print("...pulling borrows")
    CompV1["borrow"]    = CompV1["contract"].events.BorrowTaken.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    print("...pulling repays")
    CompV1["repay"]     = CompV1["contract"].events.BorrowRepaid.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    print("...pulling liquidations")
    CompV1["liquidate"] = CompV1["contract"].events.BorrowLiquidated.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    for action in actions:
        # Liquidations have different event structure than
        # other actions, so we need to handle them differently:
        if action == "liquidate":
            for event in CompV1[action]:
                block = str(event['blockNumber'])
                txhash = str(event['transactionHash'].hex())
                liquidator = str(event['args']['liquidator'])
                asset = str(event['args']['assetBorrow'])
                thisToken = 'UNK' # default label if token label not found
                for token in V1Tokens:
                    if asset == token["address"]:
                        thisToken = token["label"]
                        decimals = str(token["decimals"])
                        base = pow(10.,token["decimals"])
                amount = str(event['args']['amountRepaid'])
                borrower = str(event['args']['targetAccount'])
                data = [block,txhash,liquidator,action,thisToken,decimals,amount,borrower]
                liqOutfile.write(','.join(data[i] for i in range(len(data)))+'\n')
        else:
            for event in CompV1[action]:
                block = str(event['blockNumber'])
                txhash = str(event['transactionHash'].hex())
                address = str(event['args']['account'])
                asset = str(event['args']['asset'])
                startingBalance = str(event['args']['startingBalance'])
                newBalance = str(event['args']['newBalance'])
                amount = str(event['args']['amount'])
                # The correct amount for borrows only is "borrowAmountWithFee"
                if action == "borrow":
                    amount = str(event['args']['borrowAmountWithFee'])
                thisToken = 'UNK' # default label if token label not found
                for token in V1Tokens:
                    if asset == token["address"]:
                        thisToken = token["label"]
                        decimals = str(token["decimals"])
                data = [block,txhash,address,action,thisToken,decimals,amount,startingBalance,newBalance]
                outfile.write(','.join(data[i] for i in range(len(data)))+'\n')
    if endBlock > EarlyUserCutoffBlock:
        break
outfile.close()
liqOutfile.close()

# Gather Compound V2 Early User Interactions
actions = ["supply","withdraw","borrow","repay","liquidate","transfer"]
outfile = open(CompoundV2Outfile,'w')
liqOutfile = open(CompoundV2LiqOutfile,'w')
transferOutfile = open(CompoundV2TransferOutfile,'w')
outfile.write("block,txhash,address,action,token,decimals,amount,state\n")
liqOutfile.write("block,txhash,liquidator,action,token,decimals,amount,seizeTokens,borrower\n")
transferOutfile.write("block,txhash,sender,action,token,decimals,amount,receiver\n")
lastAction = 'None'
# Open ABI and gather events for each V2 cToken contract
for cToken in cTokens:
    token = str(cToken["abi"].split('.')[0])
    underlying = token[1:]
    with open('abis/'+cToken["abi"]) as json_file:
        cTokenABI = json.load(json_file)
    cToken["contract"] = w3.eth.contract(cToken["address"],abi=cTokenABI)
    print("Opening " + token + " V2 contract...")
    txhashList = []
    for batch in range(cZRXdeployBlock,EarlyUserCutoffBlock,batchSize):
        startBlock = batch
        endBlock = batch+batchSize-1
        print("  Collecting logs for batch from " + str(startBlock) + " to " + str(endBlock))
        if endBlock > EarlyUserCutoffBlock:
            endBlock = EarlyUserCutoffBlock
        cToken['supply']    = cToken['contract'].events.Mint.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        cToken['withdraw']  = cToken['contract'].events.Redeem.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        cToken['borrow']    = cToken['contract'].events.Borrow.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        cToken['repay']     = cToken['contract'].events.RepayBorrow.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        cToken['liquidate'] = cToken['contract'].events.LiquidateBorrow.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        cToken['transfer']  = cToken['contract'].events.Transfer.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        for action in actions:
            for event in cToken[action]:
                block = str(event['blockNumber'])
                txhash = str(event['transactionHash'].hex())
                thisToken = underlying
                # Brute-forcing the determination of correct decimals
                # because the cleaner route used for V1 doesn't work here
                if thisToken == 'USDC':
                    decimals = 6
                elif thisToken == 'WBTC':
                    decimals = 8
                else:
                    decimals = 18
                base = pow(10.,decimals)
                decimals = str(decimals)
                if action == 'supply':
                    address = str(event['args']['minter'])
                    amount = str(event['args']['mintAmount'])
                    state = str(event['args']['mintTokens'])
                    data = [block,txhash,address,action,thisToken,decimals,amount,state]
                    outfile.write(','.join(data[i] for i in range(len(data)))+'\n')
                elif action == 'withdraw':
                    address = str(event['args']['redeemer'])
                    amount = str(event['args']['redeemAmount'])
                    state = str(event['args']['redeemTokens'])
                    data = [block,txhash,address,action,thisToken,decimals,amount,state]
                    outfile.write(','.join(data[i] for i in range(len(data)))+'\n')
                elif action == 'borrow':
                    address = str(event['args']['borrower'])
                    amount = str(event['args']['borrowAmount'])
                    state = str(event['args']['accountBorrows'])
                    data = [block,txhash,address,action,thisToken,decimals,amount,state]
                    outfile.write(','.join(data[i] for i in range(len(data)))+'\n')
                elif action == 'repay':
                    address = str(event['args']['borrower'])
                    amount = str(event['args']['repayAmount'])
                    state = str(event['args']['accountBorrows'])
                    data = [block,txhash,address,action,thisToken,decimals,amount,state]
                    outfile.write(','.join(data[i] for i in range(len(data)))+'\n')
                elif action == 'liquidate':
                    liquidator = str(event['args']['liquidator'])
                    borrower = str(event['args']['borrower'])
                    amount = str(event['args']['repayAmount'])
                    seizeTokens = str(event['args']['seizeTokens'])
                    data = [block,txhash,liquidator,action,thisToken,decimals,amount,seizeTokens,borrower]
                    liqOutfile.write(','.join(data[i] for i in range(len(data)))+'\n')
                elif action == 'transfer':
                    # Only record transfers if the transfer was *not* issued as part of another event;
                    # most other actions are accompanied by a transfer to/from the user
                    # that's already (implicitly) accounted for by the other event handlers
                    if txhash not in txhashList or lastAction == 'transfer': 
                        sender = str(event['args']['from'])  
                        receiver = str(event['args']['to'])
                        amount = str(event['args']['amount'])
                        data = [block,txhash,sender,action,thisToken,decimals,amount,receiver]
                        transferOutfile.write(','.join(data[i] for i in range(len(data)))+'\n')
                        
                txhashList.append(txhash)
                lastAction = action
        if endBlock > EarlyUserCutoffBlock:
            break
outfile.close()
liqOutfile.close()
transferOutfile.close()
