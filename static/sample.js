//To enable wallet connect, an infuraID is needed, so this should be set first
KV.set_infuraID("f2be8a3bf04d4a528eb416566f7b5ad6");
//The wallet connection system can be then be initialised, and other dependency scripts can be added
KV.init(["/static/KV.WalletUIHandler.latest.min.js"]).then(function (res) {
  console.log(KV.rpc_codes)
  let walletui = new KV.WalletUIHandler({
    parent_container: document.getElementById("connect_box"),
    btn_connect: document.getElementById("connect_btn"),
    modal_connect_headline: "",
    btn_disconnect_label: "Disconnect",
    web3network: KV.rpc_codes.ETH_MAINNET,
    buttonCustom: document.getElementById("requestPermission"),
    //coinbaseButton: document.getElementById("kvwalletmodal_coinbase_btn")
  });
  walletui.on("btnconnect_clicked", function (activity_when) {
    console.log("btnconnect", activity_when);
  });
  walletui.on("modal_open", function (msg) {
    console.log("modal opened", msg);
  });
  walletui.on("modal_closed", function (msg) {
    console.log("modal closed", msg);
  });
  walletui.on("wallet_connecting", function (msg) {
    console.log("connecting", msg);
  });
  walletui.on("wallet_connected", function (msg) {
    console.log("connected", msg);
    KV.wallet.web3().eth.getAccounts().then(function (f) { console.log(f) })
    
  });
  walletui.on("wallet_error", function (msg) {
    console.log("wallet err", msg);
  });
  walletui.on("wallet_disconnected", function (msg) {
    console.log("wallet disconnected", msg);
  });

}).catch(function (err) {
  console.error(err);
});
