import web3
import json

base = 1.e18		# number of decimals for token balances
batchSize = 100000      # size of each batch of blocks;
                        # we use this to sidestep limit on
                        # number of events returned by getLogs()

CompoundV1Outfile = 'CompoundV1.EarlyUsers.csv'
CompoundV2Outfile = 'CompoundV2.EarlyUsers.csv'

# Compound V1 contract metadata
CompV1 = {
  "address"     : '0x3FDA67f7583380E67ef93072294a7fAc882FD7E7',
  "deployBlock" : 6400278,
  "abi"         : 'CompoundV1.abi.json'
}
ZRX = {
  "address"     : '0xE41d2489571d322189246DaFA5ebDe1F4699F498',
   "label"      : 'ZRX'
}
BAT = {
  "address"     : '0x0D8775F648430679A709E98d2b0Cb6250d2887EF',
  "label"       : 'BAT'
}
REP = {
  "address"     : '0x1985365e9f78359a9B6AD760e32412f4a445E862',
  "label"       : 'REP'
}
WETH = {
  "address"     : '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
  "label"       : 'WETH'
}
SAI = {
  "address"     : '0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359',
  "label"       : 'SAI'
}
V1Tokens = [ZRX,BAT,REP,WETH,SAI]

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
  "abi"         : 'cREP.abi.json'
}
cETH = {
  "address"     : '0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5',
  "deployBlock" : 7710758,
  "abi"         : 'cETH.abi.json'
}
cUSDC = {
  "address"     : '0x39AA39c021dfbaE8faC545936693aC917d5E7563',
  "deployBlock" : 7710760,
  "abi"         : 'cUSDC.abi.json'
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
actions = ["supply","withdraw","borrow","repay","liquidate"]

# No need to review blocks prior to first cToken deployment (cZRX);
# No need to review blocks after deployment of COMP token
CompV1deployBlock = CompV1["deployBlock"]
cZRXdeployBlock   = cZRX["deployBlock"]
COMPdeployBlock   = 9601359

# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
# --> User must provide a valid Infura Project ID or replace with a local ethereum IPC 
w3 = web3.Web3(web3.Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR-PROJECT-ID'))

# Gather Compound V1 Early User Interactions
# Open ABI and gather events for the V1 contract
with open(CompV1["abi"]) as json_file:
    CompoundV1ABI = json.load(json_file)
    MoneyMarketABI = CompoundV1ABI["MoneyMarket"]
outfile = open(CompoundV1Outfile,'w')

for batch in range(CompV1deployBlock,COMPdeployBlock,batchSize):
    startBlock = batch
    endBlock = batch+batchSize-1
    if endBlock > COMPdeployBlock:
        endBlock = COMPdeployBlock
    CompV1["contract"] = w3.eth.contract(CompV1["address"],abi=MoneyMarketABI)
    CompV1["supply"]    = CompV1["contract"].events.SupplyReceived.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    CompV1["withdraw"]  = CompV1["contract"].events.SupplyWithdrawn.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    CompV1["borrow"]    = CompV1["contract"].events.BorrowTaken.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    CompV1["repay"]     = CompV1["contract"].events.BorrowRepaid.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    CompV1["liquidate"] = CompV1["contract"].events.BorrowLiquidated.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
    for action in actions:
        # Liquidations have different event structure than
        # other actions, so we need to handle them differently.
        # Here we track the liquidator but not the borrower,
        # as the borrower's action will be counted later.
        if action == "liquidate":
            for event in CompV1[action]:
                block = str(event['blockNumber'])
                address = str(event['args']['liquidator'])
                asset = str(event['args']['assetBorrow'])
                thisToken = 'UNK' # default label if token label not found
                for token in V1Tokens:
                    if asset == token["address"]:
                        thisToken = token["label"]
                amount = str(round(event['args']['amountRepaid']/base,6))
                data = [block, address, action, amount, thisToken]
                outfile.write(','.join(data[i] for i in range(5))+'\n')
        else:
            for event in CompV1[action]:
                block = str(event['blockNumber'])
                address = str(event['args']['account'])
                asset = str(event['args']['asset'])
                thisToken = 'UNK' # default label if token label not found
                for token in V1Tokens:
                    if asset == token["address"]:
                        thisToken = token["label"]
                amount = str(round(event['args']['amount']/base,6))
                data = [block, address, action, amount, thisToken]
                outfile.write(','.join(data[i] for i in range(5))+'\n')
outfile.close()

# Gather Compound V2 Early User Interactions
outfile = open(CompoundV2Outfile,'w')
# Open ABI and gather events for each V2 cToken contract
for cToken in cTokens:
    token = str(cToken["abi"].split('.')[0])
    underlying = token[1:]
    with open(cToken["abi"]) as json_file:
        cTokenABI = json.load(json_file)
    cToken["contract"] = w3.eth.contract(cToken["address"],abi=cTokenABI)
    for batch in range(cZRXdeployBlock,COMPdeployBlock,batchSize):
        startBlock = batch
        endBlock = batch+batchSize-1
        if endBlock > COMPdeployBlock:
            endBlock = COMPdeployBlock
        cToken["supply"]    = cToken["contract"].events.Mint.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        cToken["withdraw"]  = cToken["contract"].events.Redeem.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        cToken["borrow"]    = cToken["contract"].events.Borrow.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        cToken["repay"]     = cToken["contract"].events.RepayBorrow.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        cToken["liquidate"] = cToken["contract"].events.LiquidateBorrow.getLogs(
                               fromBlock=startBlock,toBlock=endBlock)
        for action in actions:
            for event in cToken[action]:
                block = str(event['blockNumber'])
                thisToken = underlying
                if action == 'supply':
                    address = str(event['args']['minter'])
                    amount = str(round(event["args"]["mintAmount"]/base,6))
                elif action == 'withdraw':
                    address = str(event['args']['redeemer'])
                    amount = str(round(event["args"]["redeemAmount"]/base,6))
                elif action == 'borrow':
                    address = str(event['args']['borrower'])
                    amount = str(round(event["args"]["borrowAmount"]/base,6))
                elif action == 'repay':
                    address = str(event['args']['payer'])
                    amount = str(round(event["args"]["repayAmount"]/base,6))
                elif action == 'liquidate':
                    address = str(event['args']['liquidator'])
                    amount = str(round(event["args"]["repayAmount"]/base,6))
                data = [block, address, action, amount, thisToken]
                outfile.write(','.join(data[i] for i in range(5))+'\n')
outfile.close()


