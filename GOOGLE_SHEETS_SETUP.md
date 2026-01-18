# Google Sheets 集成设置指南

## 步骤 1: 创建 Google Sheet

1. 访问 [Google Sheets](https://sheets.google.com)
2. 创建新的电子表格，命名为 "Polymarket Insider Alerts"
3. 在第一行添加以下列标题：

```
timestamp | user_address | user_name | bet_size_usdc | outcome | market | category | account_age_days | trade_count | transaction_hash | trade_id
```

## 步骤 2: 创建 Google Apps Script

1. 在 Google Sheet 中，点击 **扩展程序 > Apps Script**
2. 删除默认代码，粘贴以下代码：

```javascript
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = JSON.parse(e.postData.contents);
    
    // 添加新行
    sheet.appendRow([
      data.timestamp || new Date().toISOString(),
      data.user_address || '',
      data.user_name || '',
      data.bet_size_usdc || '',
      data.outcome || '',
      data.market || '',
      data.category || '',
      data.account_age_days || '',
      data.trade_count || '',
      data.transaction_hash || '',
      data.trade_id || ''
    ]);
    
    return ContentService.createTextOutput(JSON.stringify({
      'status': 'success',
      'message': 'Data added successfully'
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      'status': 'error',
      'message': error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput("Polymarket Insider Alerts API is running");
}
```

3. 点击 **部署 > 新建部署**
4. 选择类型为 **Web 应用**
5. 设置：
   - 描述：Polymarket Alerts Webhook
   - 执行身份：我自己
   - 谁可以访问：**任何人**（重要！）
6. 点击 **部署**
7. 复制生成的 **Web 应用 URL**

## 步骤 3: 配置 GitHub Secrets

1. 访问你的 GitHub 仓库
2. 进入 **Settings > Secrets and variables > Actions**
3. 点击 **New repository secret**
4. 添加：
   - Name: `GOOGLE_SHEETS_WEBHOOK`
   - Value: 粘贴你的 Web 应用 URL

## 步骤 4: 更新 GitHub Actions Workflow

确保你的 `.github/workflows/hourly_report.yml` 包含新的环境变量：

```yaml
- name: Run script
  env:
    TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
    GOOGLE_SHEETS_WEBHOOK: ${{ secrets.GOOGLE_SHEETS_WEBHOOK }}
  run: python polymarket_agent.py
```

## 使用 Google Sheets 的筛选功能

设置完成后，你可以在 Google Sheets 中：

1. **创建筛选器**：选择数据区域 > 数据 > 创建筛选器
2. **按类别筛选**：点击 "category" 列的筛选按钮
3. **按金额排序**：点击 "bet_size_usdc" 列排序
4. **按时间筛选**：使用 "timestamp" 列筛选特定日期

## 可选：创建数据透视表

1. 选择所有数据
2. 插入 > 数据透视表
3. 设置：
   - 行：category
   - 值：bet_size_usdc (求和)
   
这样可以看到每个类别的总投注金额。

## 故障排除

如果数据没有写入 Google Sheets：

1. 检查 Apps Script 是否正确部署
2. 确认访问权限设置为"任何人"
3. 查看 Apps Script 执行日志：扩展程序 > Apps Script > 执行
4. 确认 GitHub Secret 中的 URL 正确无误
