# Google Sheets 集成设置指南

## 步骤 1: 创建 Google Sheet

1. 访问 [Google Sheets](https://sheets.google.com)
2. 创建新的电子表格，命名为 "Polymarket Insider Alerts"
3. 在第一行 (A1 到 K1) 添加以下列标题：

| A | B | C | D | E | F | G | H | I | J | K |
|---|---|---|---|---|---|---|---|---|---|---|
| timestamp | user_address | user_name | bet_size_usdc | outcome | market | category | account_age_days | trade_count | transaction_hash | trade_id |

## 步骤 2: 创建 Google Apps Script

1. 在 Google Sheet 中，点击 **扩展程序 > Apps Script**
2. **删除所有默认代码**（确保编辑器完全为空）
3. 复制并粘贴以下代码（确保完整复制）：

```javascript
function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  
  try {
    var data = JSON.parse(e.postData.contents);
    
    sheet.appendRow([
      data.timestamp || new Date().toISOString(),
      data.user_address || "",
      data.user_name || "",
      data.bet_size_usdc || "",
      data.outcome || "",
      data.market || "",
      data.category || "",
      data.account_age_days || "",
      data.trade_count || "",
      data.transaction_hash || "",
      data.trade_id || ""
    ]);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success"
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput("Polymarket Alerts API is running. Use POST to add data.");
}
```

4. 按 `Ctrl+S` (或 `Cmd+S`) 保存
5. 点击 **部署 > 新建部署**
6. 点击齿轮图标，选择 **Web 应用**
7. 设置：
   - **描述**: Polymarket Alerts Webhook
   - **执行身份**: 我自己
   - **谁可以访问**: **任何人** ⚠️ 这个很重要！
8. 点击 **部署**
9. 点击 **授权访问**，按提示完成授权
10. 复制生成的 **Web 应用 URL**（格式类似：`https://script.google.com/macros/s/xxx.../exec`）

## 步骤 3: 测试 Web App

在终端运行以下命令测试（替换 YOUR_URL）：

```bash
curl -X POST "YOUR_URL" \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2026-01-19T12:00:00Z","user_address":"0xtest","user_name":"test","bet_size_usdc":5000,"outcome":"Yes","market":"Test Market","category":"测试","account_age_days":10,"trade_count":5,"transaction_hash":"0xabc","trade_id":"test123"}'
```

如果成功，会返回 `{"status":"success"}`，并且 Google Sheet 会新增一行。

## 步骤 4: 配置 GitHub Secrets

1. 访问你的 GitHub 仓库: https://github.com/josepumpbtc/Polymaretinsidermonitor
2. 进入 **Settings > Secrets and variables > Actions**
3. 点击 **New repository secret**
4. 添加：
   - **Name**: `GOOGLE_SHEETS_WEBHOOK`
   - **Value**: 粘贴你的 Web 应用 URL

## 常见问题

### 错误: TypeError: "" is not a function

**原因**: Apps Script 代码没有正确复制，或者有多余/缺少的字符。

**解决方案**:
1. 删除 Apps Script 中的所有代码
2. 重新完整复制上面的代码
3. 保存并重新部署（点击 **部署 > 管理部署 > 编辑 > 新版本 > 部署**）

### 错误: 403 Forbidden

**原因**: Web App 的访问权限设置错误。

**解决方案**:
1. 部署 > 管理部署 > 编辑
2. 确保"谁可以访问"设置为"任何人"
3. 重新部署

### 数据没有写入

**原因**: 可能是 POST 请求失败或数据格式问题。

**解决方案**:
1. 在 Apps Script 中查看执行日志：**执行 > 查看执行记录**
2. 检查 GitHub Actions 日志中的错误信息

### 如何查看 Apps Script 日志

1. 打开 Apps Script 编辑器
2. 点击左侧 **执行** 图标
3. 查看每次调用的详细信息和错误

## 重新部署步骤（如果需要更新代码）

1. 修改 Apps Script 代码
2. 保存 (`Ctrl+S`)
3. 点击 **部署 > 管理部署**
4. 点击编辑图标（铅笔）
5. **版本** 选择 **新版本**
6. 点击 **部署**
7. 新的 URL 保持不变，无需更新 GitHub Secret

## Google Sheet 链接

你的 Google Sheet: https://docs.google.com/spreadsheets/d/1MrNC0e_plznfvNZXOGk0a28UobJ-SMg1y_0C9UQgxhs/edit

## 使用筛选功能

设置完成后，在 Google Sheets 中：

1. **创建筛选器**: 选择数据区域 > 数据 > 创建筛选器
2. **按类别筛选**: 点击 "category" 列的筛选按钮
3. **按金额排序**: 点击 "bet_size_usdc" 列排序
