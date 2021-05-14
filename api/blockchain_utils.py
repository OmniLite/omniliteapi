import requests
import json, re
from rpcclient import *
from cacher import *
from debug import *
from common import *
import random
import config

try:
  expTime=config.BTCBAL_CACHE
except:
  expTime=600

try:
  TESTNET = (config.TESTNET == 1)
except:
  TESTNET = False

def bc_getutxo(address, ramount):
  avail=0
  try:
    r=getaddressutxos(address)
    if r['error'] == None:
      retval=[]
      unspents = r['result']
      for tx in sorted(unspents, key = lambda i: i['satoshis'],reverse=True):
        txUsed=gettxout(tx['txid'],tx['outputIndex'])['result']
        isUsed = txUsed==None
        if not isUsed:
          coinbaseHold = (txUsed['coinbase'] and txUsed['confirmations'] < 100)
          multisigSkip = ("scriptPubKey" in txUsed and txUsed['scriptPubKey']['type'] == "multisig")
          if not coinbaseHold and txUsed['confirmations'] > 0 and not multisigSkip:
            avail += tx['satoshis']
            retval.append([ tx['txid'], tx['outputIndex'], tx['satoshis'] ])
            if avail >= ramount:
              return {"avail": avail, "utxos": retval, "error": "none"}
      return {"avail": avail, "error": "Low balance error"}
    else:
      return {"avail": avail, "error": r['error']}
  except Exception as e:
    return {"avail": avail, "error": e.message}

def bc_getpubkey(address):
  pubkey = ""
  ckey="omniwallet:pubkey:address:"+str(address)
  try:
    pubkey=rGet(ckey)
    pubkey=str(pubkey)
    if pubkey in [None, ""]:
      raise "error loading pubkey"
  except:
    r=getaddressdeltas(address)
    if r['error']==None:
      txlist=r['result']
      for tx in txlist:
        if tx['satoshis']<0:
          try:
            #found spending tx
            rawtx=getrawtransaction(tx['txid'])
            pubkey = str(rawtx['result']['vin'][tx['index']]['scriptSig']['asm'].split(' ')[1])
            break
          except:
            #problem parsing tx try next one
            pass
  if pubkey not in [None, ""]:
    #cache pubkey for a month, it doesn't change
    rSet(ckey,pubkey)
    rExpire(ckey,2628000)
  return pubkey

def bc_getbalance(address):
  rev=raw_revision()
  cblock=rev['last_block']
  ckey="omniwallet:balances:address:"+str(address)+":"+str(cblock)
  try:
    balance=rGet(ckey)
    balance=json.loads(balance)
    if balance['error']:
      raise LookupError("Not cached")
    pending = getPending(address)
    balance['pendingpos'] = pending['pos']
    balance['pendingneg'] = pending['neg']
  except Exception as e:
    balance = {'bal': 0, 'pendingpos': 0, 'pendingneg': 0, 'error': 'undefined'}
    try:
      r=getaddressbalance(address)
      if r['error'] == None:
        resp = r['result']
        bal = resp['balance']
        pending = getPending(address)
        balance = {'bal': bal, 'pendingpos': pending['pos'], 'pendingneg': pending['neg'], 'error': None}
      else:
        balance['error'] = r['error']
    except Exception as e:
      balance['error'] = str(e.message)
    #cache btc balances for block
    rSet(ckey,json.dumps(balance))
    rExpire(ckey,expTime)
  return balance

def getPending(address):
  r = getaddressmempool(address)
  pos = 0
  neg = 0
  if r['error'] == None:
    mempool = r['result']
    for entry in mempool:
      sat = entry['satoshis']
      if sat > 0:
        pos += sat
      else:
        neg -= sat
  return {'pos':pos, 'neg':neg}