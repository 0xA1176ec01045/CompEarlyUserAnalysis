import web3
import json
from hexbytes import HexBytes

detailedPrint = False
base = 1.e18

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

# No need to review blocks prior to first cToken deployment (cZRX);
# No need to review blocks after deployment of COMP token
cZRXdeployBlock = cZRX["deployBlock"]
COMPdeployBlock = 9601359

# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
# --> User must provide a valid Infura Project ID or replace with a local ethereum RPC 
w3 = web3.Web3(web3.Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR-PROJECT-ID'))

# Open ABIs for each cToken contract
CTokenContracts = []
for cToken in cTokens:
    with open(cToken["abi"]) as json_file:
        cTokenABI = json.load(json_file)
    cToken["contract"] = w3.eth.contract(cToken["address"],abi=cTokenABI)
    
# Review relevant blocks for interactions with cToken contracts
# --> Known examples for validation testing:
# ----> one withdrawal from cSAI, 7824167
# ----> one supply to cSAI, 7842233
# ----> one borrow from cSAI, 8559368
# ----> one repay to cSAI, 10048941
# ----> one supply to cZRX, 7778085
# ----> one withdraw from cBAT, 7757440
for iblock in range(7842233,7842234):
#for iblock in range(cZRXdeployBlock,COMPdeployBlock):
    block = w3.eth.get_block(iblock)
    print('--- Block ' + str(iblock) + ' ---')

    # Examine each transaction from the selected block
    # --> example: extracting the 3rd tx
    # txhash = [x.hex() for x in block.transactions][2]
    # --> extension to loop over all txs
    for txhash in [x.hex() for x in block.transactions]:

        # Extract the sender and receiver of the transaction ('to', 'from')
        tx = w3.eth.getTransaction(txhash)
        txfrom = tx['from']
        txto = tx['to']

        # Report transaction under review
        if (detailedPrint):
            print('Examining tx ' + txhash + ':')
            if (txfrom == None):
                txfrom = 'None'
            if (txto == None):
                txto = 'None'
            print('... from ' + txfrom)
            print('... to   ' + txto)

        # Report all mint, redeem, borrow, or repay tx for each cToken
        for cToken in cTokens:
            cTokenName = str(cToken["abi"].split('.')[0])
            if (txto == cToken["address"]):
                input_data = cToken["contract"].decode_function_input(tx.input)
                input_fn = input_data[0].function_identifier
                if (input_fn == 'redeemUnderlying'):
                    val = float(input_data[1]['redeemAmount'])/base
                    print(txfrom + ' withdraw ' + str(val) + ' ' + cTokenName[1:])
                elif (input_fn == 'redeem'):
                    val = float(input_data[1]['redeemTokens'])/base
                    print(txfrom + ' withdraw ' + str(val) + ' ' + cTokenName)
                elif (input_fn == 'mint'):
                    val = float(input_data[1]['mintAmount'])/base
                    print(txfrom + ' supply ' + str(val) + ' ' + cTokenName[1:])
                elif (input_fn == 'borrow'):
                    val = float(input_data[1]['borrowAmount'])/base
                    print(txfrom + ' borrow ' + str(val) + ' ' + cTokenName[1:])
                elif (input_fn == 'repayBorrow'):
                    val = float(input_data[1]['repayAmount'])/base
                    print(txfrom + ' repay ' + str(val) + ' ' + cTokenName[1:])
