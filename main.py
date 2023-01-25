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

patternEth = {
    "type": "VerifiablePresentationRequest",
    "query": [
        {
            "type": "QueryByExample",
            "credentialQuery": [
                {
                    "required": True,
                    "example": {
                        "type": "Over13"
                    }
                },
                {
                    "required": True,
                    "example": {
                        "type": "EthereumAssociatedAddress"
                    }
                }
            ]
        }
    ],
    "challenge": "d0f43665-9c0a-11ed-9db1-0a1628958560",
    "domain": "https://talao.co/"
}

patternTezos = {
    
    "type": "VerifiablePresentationRequest",
    "query": [
        {
            "type": "QueryByExample",
            "credentialQuery": [
                {
                    "required": True,
                    "example": {
                        "type": "Over13"
                    }
                },
                {
                    "required": True,
                    "example": {
                        "type": "TezosAssociatedAddress"
                    }
                }
            ]
        }
    ],
    "challenge": "d0f43665-9c0a-11ed-9db1-0a1628958560",
    "domain": "https://talao.co/"
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
    app.add_url_rule('/over13-demo',  view_func=check_over13, methods = ['GET', 'POST'])
    app.add_url_rule('/over13-demo/webhook',  view_func=check_over13_webhook, methods = ['GET', 'POST'], defaults={'red' : red})
    app.add_url_rule('/over13-demo/stream',  view_func=check_over13_stream, methods = ['GET', 'POST'], defaults={'red' : red})
    global payload
    if mode.myenv == 'aws':
        payload =  'I am over 13 years old #https://talao.co/over13-demo/endpoint/'
    else :
        payload =  'I am over 13 years old #https://talao.co/over13-demo/endpoint/'
    return


def check_over13():
    try:
        blockchain = request.args['blockchain']
    except KeyError:
        return render_template('menu.html')
    logging.info("check_over13")
    global payload_gamer_pass
    id = str(uuid.uuid1())
    if blockchain=="tezos":
        patternTezos['challenge'] = str(uuid.uuid1()) # nonce
        IP=extract_ip()
        patternTezos['domain'] = 'http://' + IP
        red.set(id,  json.dumps(patternTezos))
        return render_template('check_over13.html',
                             id = id,
                             payload_gamer_pass = payload + id
                             )
    elif blockchain=="ethereum":
        patternEth['challenge'] = str(uuid.uuid1()) # nonce
        IP=extract_ip()
        patternEth['domain'] = 'http://' + IP
        red.set(id,  json.dumps(patternEth))
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


@app.route('/over13-demo/static/<filename>',methods=['GET'])
def serve_static(filename):
    logging.info(filename)
    return send_file('./static/'+filename, download_name=filename)


@app.route('/over13-demo/endpoint/<id>', methods = ['GET', 'POST'],  defaults={'red' : red})
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
        return jsonify("ok"), 200


@app.route('/over13-demo/verifier_stream', methods = ['GET'],  defaults={'red' : red})
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


@app.route('/over13-demo/followup', methods = ['GET', 'POST'],  defaults={'red' : red})
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
    typeCredential=dictionnaire["type"][1]
    print("type credential : "+typeCredential)
    if(typeCredential=="Over13"):
        print("presentation " +str(presentation))
    return None


if __name__ == '__main__':
    logging.info("app init")
    
    print(mode.server)
    app.run( host = "" , port= 2000, debug =True)
    #,ssl_context='adhoc'
    #mode.IP
init_app(app,red,mode)