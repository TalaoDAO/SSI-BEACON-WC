from flask import render_template, request, jsonify, Response,Flask,send_file,render_template_string
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
from flask_qrcode import QRcode


app = Flask(__name__,static_folder=os.path.abspath('/home/achille/wallet-link/static'))
app.secret_key ="Talao"
red= redis.Redis(host='127.0.0.1', port=6379, db=0)
qrcode = QRcode(app)
pattern = {
    "type": "VerifiablePresentationRequest",
    "query": [
        {
            "type": "QueryByExample",
            "credentialQuery": [
                {
                    "required": True,
                    "example": {
                        "type": "Over18"
                    }
                },
                
            ]
        }
    ],
    "challenge": "d0f43665-9c0a-11ed-9db1-0a1628958560",
    "domain": "https://talao.co/"
}
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
                        "type": "EthereumPooAddress"
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
                        "type": "TezosPooAddress"
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
    app.add_url_rule('/over13-demo/over18-demo',  view_func=check_over18, methods = ['GET', 'POST'])
    app.add_url_rule('/over13-demo/over18-demo/webhook',  view_func=check_over18_webhook, methods = ['GET', 'POST'], defaults={'red' : red})
    app.add_url_rule('/over13-demo/over18-demo/stream',  view_func=check_over18_stream, methods = ['GET', 'POST'], defaults={'red' : red})
    global payload
    if mode.myenv == 'aws':
        payload =  'I am over 13 years old #https://talao.co/over13-demo/endpoint/'
    else :
        payload =  'I am over 13 years old #https://talao.co/over13-demo/endpoint/'    
    global payload18
    if mode.myenv == 'aws':
        payload18 =  'https://talao.co/over13-demo/over18-demo/endpoint/'
    else :
        payload18 =  'https://5118-2a01-e34-ec69-84a0-73c8-931d-6fff-15b3.eu.ngrok.io/over13-demo/over18-demo/endpoint/'
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


def check_over18():

    logging.info("check_over18")
    id = str(uuid.uuid1())
    pattern['challenge'] = str(uuid.uuid1()) # nonce
    IP=extract_ip()
    pattern['domain'] = 'http://' + IP
    red.set(id,  json.dumps(pattern))
    html_string="""<html>
<head>
  <link rel="stylesheet" href="/over13-demo/static/style18.css">
  <title>SSI - Web3 integration with an dApp-to-wallet web3 protocol.</title>
  <link rel="icon" type="image/png" href="https://ucarecdn.com/1c1db4c6-4cf3-45ff-a79c-9e30f5062523/" sizes="16x16">
</head>
<body>
<nav class="js-nav nav-02  nav-02--sticky  nav-02--sticky--white  ">
    <div class="nav-02__box">
      <div class="nav-02__logo"><a class="nav-02__link" href="https://talao.io/" target="_self">
          <img loading="lazy" class="nav-02__logo_img" src="https://unicorn-cdn.b-cdn.net/24a9fea5-9913-463c-9dd7-1f34e01531f5/" height="33px" alt="Logo" />
        </a></div>

      <div class="nav-02__list_wrapper  ">
        <div class="nav-02__list nav-02__list--desktop">
          <div class="nav-02__item">
            <a class="button   button--black-outline  button--empty " href="https://talao.io/#slider-07-879531"
              target="_self">
              <p class="linkP"> Wallet features
              </p>
            </a>
          </div>
          <div class="nav-02__item" id="newsNav">
            <a class="button   button--black-outline  button--empty " href="https://talao.io/#posts-05-876621"
              target="_self">
              <p class="linkP">News</p>

            </a>
          </div>
          <div class="nav-02__item" id="roadmapNav">
            <a href="https://talao.io/#features-09-390941" target="_self">
              <p class="linkP">Roadmap</p>

            </a>
          </div>
          <div class="nav-02__item" id="faqNav">
            <a class="button   button--black-outline  button--empty " href="https://talao.io/#faq-02-199311" target="_self">
              <p class="linkP">FAQ</p>
            </a>
          </div>
          <div class="nav-02__item">

            <a data-stripe-product-id="" data-stripe-mode="payment" data-successful-payment-url=""
              data-cancel-payment-url="" class="button button--accent-bg "
              href="mailto:thierry.thevenet@talao.io" target="_blank">
              <div class="contactSpan">
                <p class="contactP">Contact</p>
              </div>
            </a>
          </div>
        </div>


      </div>

    </div>

  </nav>
  <div class=" text-center">
    <div id="pairing">
      <p class="my-5">Scannez ce qr code pour présenter votre certificat de majorité</p>
    </div>
    <div id="intro">
      <p class="mb-5"></p>
                <div><img style="width:300px;height:300px" id="qrcode" src="{{ qrcode(url) }}" ></div>    </div>
    <!--<div id="haveover18">
      <div id="webhook">
        <p id="devCorner">The Developers' Corner : data received on webhook</p>
        <textarea id="dataSent" rows="10" cols="100"></textarea>
      </div>
    </div>-->
  </div>
  <script>
    var source = new EventSource('/over13-demo/over18-demo/verifier_stream');
    source.onmessage = function (event) {
      const result = JSON.parse(event.data);
      if (result.check == 'ok' & result.id == '{{id}}') {
        //window.alert("over18")

        document.getElementById("qrcode").setAttribute("src","https://talao.co/altme-identity/static/tick-circle.png") 
      }
      else {
        //window.alert(result.message);
        //window.location.href="/analytics/";
      }
    };
  </script>
</body>
</html>"""
    return render_template_string(html_string,id = id,url = payload18 + id)
    #return render_template('check_over18.html',id = id,payload_gamer_pass = payload + id)


def check_over18_webhook(red) :
    data = request.get_json()
    print("data received = ", data)
    if data['event'] == 'VERIFICATION' :
        if  "over18" in data["vc_type"]  :
            event_data = json.dumps({"over18" : 'verified',
                                    'id' : data['id'],
                                     'data' : json.dumps(data)})
            red.publish('check_over18', event_data)
    return jsonify('ok')


def check_over18_stream(red):
    def event_stream18(red):
        pubsub = red.pubsub()
        pubsub.subscribe('check_over18')
        for message in pubsub.listen():
            if message['type']=='message':
                yield 'data: %s\n\n' % message['data'].decode()
    headers = { "Content-Type" : "text/event-stream",
                "Cache-Control" : "no-cache",
                "X-Accel-Buffering" : "no"}
    return Response(event_stream(red), headers=headers)




@app.route('/over13-demo/over18-demo/endpoint/<id>', methods = ['GET', 'POST'],  defaults={'red' : red})
def presentation_endpoint18(id, red):
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
                    'presented' : datetime.datetime.now().replace(microsecond=0).isoformat() + "Z",
                    'vc_type' : "over18",
                    "verification" : "verification"
            }
         
                                })           
        red.publish('verifier', event_data)
        return jsonify("ok"), 200


@app.route('/over13-demo/over18-demo/verifier_stream', methods = ['GET'],  defaults={'red' : red})
def presentation_stream18(red):
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


@app.route('/over13-demo/over18-demo/followup', methods = ['GET', 'POST'],  defaults={'red' : red})
def followup18(red):  
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
    if(typeCredential=="Over18"):
        print("presentation " +str(presentation))
    return None

if __name__ == '__main__':
    logging.info("app init")
    
    print(mode.server)
    app.run( host = "" , port= 2000, debug =True)
    #,ssl_context='adhoc'
    #mode.IP
init_app(app,red,mode)