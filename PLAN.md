# Aider 斜杠命令参考

## Context
用户想要了解aider有哪些斜杠命令可以参考。通过分析aider的源代码（`/home/smh/aider/aider/commands.py`），我整理出了所有可用的斜杠命令。

## 斜杠命令列表

根据aider源代码中的`cmd_`方法，以下是所有可用的斜杠命令：

### 模型相关命令
1. `/model` - 切换主模型到新的LLM
2. `/editor-model` - 切换编辑器模型到新的LLM
3. `/weak-model` - 切换弱模型到新的LLM
4. `/chat-mode` - 切换到新的聊天模式（如ask、code、architect、context等）
5. `/models` - 搜索可用模型列表

### 文件管理命令
6. `/add` - 添加文件到聊天，以便aider可以编辑或详细审查它们
7. `/drop` - 从聊天会话中移除文件以释放上下文空间
8. `/read-only` - 添加只读文件到聊天，或将已添加文件转为只读
9. `/ls` - 列出所有已知文件并标记哪些包含在聊天会话中

### 聊天模式命令
10. `/ask` - 关于代码库提问而不编辑任何文件。如果没提供提示，切换到ask模式
11. `/code` - 请求代码更改。如果没提供提示，切换到code模式
12. `/architect` - 进入architect/editor模式使用两个不同模型。如果没提供提示，切换到architect/editor模式
13. `/context` - 进入context模式查看周围代码上下文。如果没提供提示，切换到context模式
14. `/ok` - `/code Ok, please go ahead and make those changes.`的别名（任何参数都会被追加）

### 版本控制命令
15. `/commit` - 提交在聊天之外对仓库所做的编辑（提交消息可选）
16. `/undo` - 撤销aider所做的最后一次git提交
17. `/diff` - 显示自上次消息以来的更改差异
18. `/git` - 运行git命令（输出不包含在聊天中）
19. `/lint` - 对聊天中的文件或所有脏文件进行lint和修复

### 上下文和令牌管理命令
20. `/tokens` - 报告当前聊天上下文使用的令牌数量
21. `/clear` - 清除聊天历史
22. `/reset` - 移除所有文件并清除聊天历史
23. `/map` - 打印当前仓库地图
24. `/map-refresh` - 强制刷新仓库地图

### 工具和实用命令
25. `/run` - 运行shell命令并可选择将输出添加到聊天（别名：`!`）
26. `/test` - 运行shell命令并在非零退出代码时将输出添加到聊天
27. `/web` - 抓取网页，转换为markdown并在消息中发送
28. `/voice` - 录制和转录语音输入
29. `/paste` - 将剪贴板中的图像/文本粘贴到聊天中
30. `/copy` - 将最后一条助手消息复制到剪贴板
31. `/copy-context` - 将当前聊天上下文复制为markdown，适合粘贴到Web UI

### 配置和设置命令
32. `/settings` - 打印当前设置
33. `/load` - 从文件加载并执行命令
34. `/save` - 将可以重建当前聊天会话文件的命令保存到文件
35. `/multiline-mode` - 切换多行模式（交换Enter和Meta+Enter的行为）
36. `/think-tokens` - 设置思考令牌预算
37. `/reasoning-effort` - 设置推理努力级别

### 帮助和报告命令
38. `/help` - 关于aider提问
39. `/report` - 通过打开GitHub Issue报告问题
40. `/editor` - 打开编辑器编写提示
41. `/edit` - `/editor`的别名：打开编辑器编写提示

### 退出命令
42. `/exit` - 退出应用程序
43. `/quit` - 退出应用程序（`/exit`的别名）

## 特殊命令
- `!` - 运行shell命令（`/run`的别名）

## 实施说明
这些命令都是通过`Commands`类中的`cmd_`方法定义的。每个命令都接受一个`args`参数，并且大多数都有相应的文档字符串（`__doc__`）来描述其功能。

## 验证
要查看aider的完整斜杠命令列表，可以在aider交互界面中输入`/help`命令，或者查看`/home/smh/aider/aider/commands.py`文件中的`get_help_md()`方法。