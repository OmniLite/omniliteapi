import re
from flask_rate_limit import *
from common import *
from debug import *
from property_service import getpropdistraw
from properties_service import rawlist
from flask import Flask

app = Flask(__name__)
app.debug = True

#TODO COnversion
@app.route('/properties')
@ratelimit(limit=12, per=60)
def properties():
  return jsonify(rawlist())


def properties_OLD():
  #ROWS=dbSelect("select * from smartproperties")
  ROWS=dbSelect("select propertyname, propertyid, protocol, propertytype from smartproperties")

  def dehexify(hex_str):
      temp_str=[]
      for let in hex_str:
          if ord(let) < 128:
              temp_str.append(let)
          else:
              temp_str.append('?')
      return ''.join(temp_str)

  response = []
  for sprow in ROWS:
      res = {
          'currencyID': sprow[1],
          #'name': dehexify(sprow[-1]['name']) 
          'name': dehexify(sprow[0]),
          'Protocol': sprow[2],
          'divisible': sprow[3] in [2,66,130]
      }
      response.append(res)

  json_response = json.dumps( sorted(response, key=lambda x:  int(x['currencyID']) ))
  return json_response

@app.route('/addresses')
@ratelimit(limit=12, per=60)
def address():
 currency_id = request.args.get('currency_id')
 currency_id = re.sub(r'\D+', '', currency_id) 
 return jsonify(getpropdistraw(str(currency_id)))



def addresses_OLD():
  currency_id = request.args.get('currency_id')
  response = []

  currency_id = re.sub(r'\D+', '', currency_id) #check alphanumeric
  ROWS=dbSelect("select address,balanceavailable,balancereserved,sp.propertytype from addressbalances ab, smartproperties sp "
                "where ab.propertyid=sp.propertyid and sp.protocol!='Fiat' and sp.propertyid=%s",[currency_id])

  for addrrow in ROWS:
      res = {
          'address': addrrow[0]
      }
      #convert property type to true/false for divisibility calculations
      divisible=isDivisibleProperty(addrrow[3])

      if currency_id == '0': #BTC
        res['balance'] = ('%.8f' % float(addrrow[1])).rstrip('0').rstrip('.')
        response.append(res)
      else:
        if divisible:
          res['balance'] = ('%.8f' % float(addrrow[1]/100000000)).rstrip('0').rstrip('.')
          res['reserved_balance'] = ('%.8f' % float(addrrow[2]/100000000)).rstrip('0').rstrip('.')
        else:
          res['balance'] = ('%.8f' % float(addrrow[1])).rstrip('0').rstrip('.')
          res['reserved_balance'] = ('%.8f' % float(addrrow[2])).rstrip('0').rstrip('.')
        response.append(res)

  json_response = json.dumps(response)
  return json_response


#@app.route('/transactions/<address>')
#@ratelimit(limit=12, per=60)
def transactions(address=None):
  currency_id = request.args.get('currency_id')

  print_debug((address, currency_id),4)

  if address == None:
    abort(400)

  currency_id = re.sub(r'\D+', '', currency_id) #check alphanumeric

  ROWS=dbSelect("select * from addressesintxs a, transactions t where a.address=%s  and a.txdbserialnum = t.txdbserialnum and a.propertyid=%s",
                (address, currency_id))

  transactions = []
  for txrow in ROWS:
      transactions.append(txrow[9])

  return jsonify({ 'address': address, 'transactions': transactions })

