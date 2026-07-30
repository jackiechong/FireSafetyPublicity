const app = getApp();

function request(options) {
  const { url, method = "GET", data } = options;
  const apiBase = app.globalData.apiBase || require("./config").apiBase;
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${apiBase}${url}`,
      method,
      data,
      header: {
        "Content-Type": "application/json",
        ...(app.globalData.token ? { Authorization: `Bearer ${app.globalData.token}` } : {}),
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          const msg = (res.data && res.data.detail) || res.errMsg || "请求失败";
          const err = new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
          err.statusCode = res.statusCode;
          err.data = res.data;
          reject(err);
        }
      },
      fail: reject,
    });
  });
}

module.exports = { request };
