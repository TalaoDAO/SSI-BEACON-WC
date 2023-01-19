from flask import render_template, request, jsonify, Response,Flask,send_file
import uuid 
import json
import logging
import redis 
import os 
import socket
import json
import logging
import sys
import environment
import datetime

app = Flask(__name__,static_folder=os.path.abspath('/home/achille/wallet-link/static'))
app.secret_key =json.dumps(json.load(open("keys.json", "r"))["appSecretKey"])
red= redis.Redis(host='127.0.0.1', port=6379, db=0)
pattern = {"type": "VerifiablePresentationRequest",
            "query": [
                {
                    "type": "QueryByExample",
                    "credentialQuery": []
                }]
            }
myenv = os.getenv('MYENV')
if not myenv :
   myenv='thierry'
mode = environment.currentMode(myenv)

def extract_ip():
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:       
        st.connect(('10.255.255.255', 1))
        IP = st.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        st.close()
    return IP

def init_app(app,red, mode) :
    app.add_url_rule('/sandbox/dapp/check_over13',  view_func=check_over13, methods = ['GET', 'POST'])
    app.add_url_rule('/sandbox/dapp/check_over13/webhook',  view_func=check_over13_webhook, methods = ['GET', 'POST'], defaults={'red' : red})
    app.add_url_rule('/sandbox/dapp/check_over13/stream',  view_func=check_over13_stream, methods = ['GET', 'POST'], defaults={'red' : red})
    global payload
    if mode.myenv == 'aws':
        payload = 'I am over 13 years old #https://talao.co/sandbox/op/beacon/verifier/tuaitvcrkl?id='
    else :
        payload =  'I am over 13 years old #https://c6c9-86-229-94-232.eu.ngrok.io/sandbox/dapp/endpoint/'
    return


def check_over13():
    try:
        blockchain = request.args['blockchain']
    except KeyError:
        return render_template('menu.html')
    logging.info("check_over13")
    global payload_gamer_pass
    id = str(uuid.uuid1())
    #id = str(uuid.uuid1())
    pattern['challenge'] = str(uuid.uuid1()) # nonce
    IP=extract_ip()
    pattern['domain'] = 'http://' + IP
    # l'idee ici est de créer un endpoint dynamique
    red.set(id,  json.dumps(pattern))
    if blockchain=="tezos":
        return render_template('check_over13.html',
                             id = id,
                             payload_gamer_pass = payload + id
                             )
    elif blockchain=="ethereum":
        return render_template('check_over13Eth.html',
                             id = id,
                             payload_gamer_pass = payload + id
                             )
    else:
        return render_template('menu.html')


  

def check_over13_webhook(red) :
    data = request.get_json()
    print("data received = ", data)
    if data['event'] == 'VERIFICATION' :
        if  "Over13" in data["vc_type"]  :
            event_data = json.dumps({"over13" : 'verified',
                                    'id' : data['id'],
                                     'data' : json.dumps(data)})
            red.publish('check_over13', event_data)
    return jsonify('ok')


def check_over13_stream(red):
    def event_stream(red):
        pubsub = red.pubsub()
        pubsub.subscribe('check_over13')
        for message in pubsub.listen():
            if message['type']=='message':
                yield 'data: %s\n\n' % message['data'].decode()
    headers = { "Content-Type" : "text/event-stream",
                "Cache-Control" : "no-cache",
                "X-Accel-Buffering" : "no"}
    return Response(event_stream(red), headers=headers)

@app.route('/static/<filename>',methods=['GET'])
def serve_static(filename):
    logging.info(filename)
    return send_file('./static/'+filename, download_name=filename)


@app.route('/sandbox/dapp/endpoint/<id>', methods = ['GET', 'POST'],  defaults={'red' : red})
def presentation_endpoint(id, red):
    print(id)
    try :
        my_pattern = json.loads(red.get(id).decode())
        print("my_pattern "+str(my_pattern))
    except :
        event_data = json.dumps({"id" : id,
                                 "message" : "redis decode failed",
                                 "check" : "ko"})
        red.publish('verifier', event_data)
        print("event data "+str(event_data))
        return jsonify("server error"), 500
    
    if request.method == 'GET':
        print("my_pattern "+str(my_pattern))
        return jsonify(my_pattern)
    
    if request.method == 'POST' :
        #red.delete(id)
        try : 
            print(request.form['presentation'])
            #result = json.loads(asyncio.run(verifyPresentation(request.form['presentation'])))
            result=False
            print("result "+str(result))
        except:
            print("except")
            event_data = json.dumps({"id" : id,
                                    "check" : "ko",
                                    "message" : "presentation is not correct"})
            red.publish('verifier', event_data)
            return jsonify("presentation is not correct"), 403
        if result :
            print("result")
            event_data = json.dumps({"id" : id,
                                    "check" : "ko",
                                    "message" : result})
            red.publish('verifier', event_data)
            return jsonify(result), 403
        # mettre les tests pour verifier la cohérence entre issuer, holder et credentialSubject.id 
        # 
        red.set(id,  request.form['presentation'])
        event_data = json.dumps({"id" : id,
                                "message" : "presentation is verified",
                                "check" : "ok",
                                "payload" : { 'event' : 'VERIFICATION',
                    'id' : id,
                    'address' : request.args['address'],
                    'presented' : datetime.datetime.now().replace(microsecond=0).isoformat() + "Z",
                    'vc_type' : "Over13",
                    "verification" : "verification"
            }
         
                                })           
        red.publish('verifier', event_data)
        
        #return redirect("/")
        return jsonify("ok"), 200

@app.route('/sandbox/dapp/verifier_stream', methods = ['GET'],  defaults={'red' : red})
def presentation_stream(red):
    def event_stream(red):
        pubsub = red.pubsub()
        pubsub.subscribe('verifier')
        for message in pubsub.listen():
            if message['type']=='message':
                yield 'data: %s\n\n' % message['data'].decode()
    headers = { "Content-Type" : "text/event-stream",
                "Cache-Control" : "no-cache",
                "X-Accel-Buffering" : "no"}
    return Response(event_stream(red), headers=headers)

@app.route('/sandbox/dapp/followup', methods = ['GET', 'POST'],  defaults={'red' : red})
def followup(red):  
    print("accessing followup")
    try :  
        presentation = json.loads(red.get(request.args['id']).decode())
    except :
        print('redis problem')
        sys.exit()
    red.delete(request.args['id'])
    holder = presentation['holder']
    # pour prendre en compte une selection multiple ou unique
    if isinstance(presentation['verifiableCredential'], dict) :
        nb_credentials = "1"
        issuers = presentation['verifiableCredential']['issuer']
        types = presentation['verifiableCredential']['type'][1]
        credential = json.dumps(presentation['verifiableCredential'], indent=4, ensure_ascii=False)
    else :
        nb_credentials = str(len(presentation['verifiableCredential']))
        issuer_list = type_list = list()
        for credential in presentation['verifiableCredential'] :
            if credential['issuer'] not in issuer_list :
                issuer_list.append(credential['issuer'])
            if credential['type'][1] not in type_list :
                type_list.append(credential['type'][1])
        issuers = ", ".join(issuer_list)
        types = ", ".join(type_list)
        # on ne presente que le premier
        credential = json.dumps(presentation['verifiableCredential'][0], indent=4, ensure_ascii=False)
    presentation = json.dumps(presentation, indent=4, ensure_ascii=False)
    dictionnaire=json.loads(credential)
    #print(presentation)
    
    typeCredential=dictionnaire["type"][1]
    print("type credential : "+typeCredential)

    if(typeCredential=="Over13"):
        print("presentation " +str(presentation))
        
    return None

if __name__ == '__main__':
    logging.info("app init")
    
    init_app(app,red,mode)
    print(mode.server)
    app.run( host = mode.IP , port= 2000, debug =True)
    #,ssl_context='adhoc'
