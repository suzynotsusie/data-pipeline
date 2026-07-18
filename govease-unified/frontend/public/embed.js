(function () {
  var current = document.currentScript;
  var base = current.getAttribute("data-base-url") || new URL(current.src).origin;
  var frame = document.createElement("iframe");
  var button = document.createElement("button");
  frame.src = base.replace(/\/$/, "") + "/widget";
  frame.title = "GovEase AI - Trợ lý dịch vụ công";
  frame.style.cssText = "display:none;position:fixed;right:20px;bottom:84px;width:min(440px,calc(100vw - 28px));height:min(720px,calc(100vh - 108px));border:0;border-radius:16px;box-shadow:0 24px 80px rgba(42,25,17,.3);background:#fff;z-index:2147483646";
  button.type = "button";
  button.textContent = "Hỏi GovEase AI";
  button.style.cssText = "position:fixed;right:20px;bottom:20px;border:0;border-radius:999px;padding:14px 20px;background:#a51c23;color:#fff;font:700 14px system-ui;box-shadow:0 8px 28px rgba(70,20,20,.3);cursor:pointer;z-index:2147483647";
  button.onclick = function () { var closed = frame.style.display === "none"; frame.style.display = closed ? "block" : "none"; button.textContent = closed ? "Đóng trợ lý" : "Hỏi GovEase AI"; };
  document.body.appendChild(frame); document.body.appendChild(button);
})();
