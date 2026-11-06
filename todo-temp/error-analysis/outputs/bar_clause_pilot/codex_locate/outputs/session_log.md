# Codex 人工阅读定位记录

## 2026年11月6日，本次会话

会话开始时不存在 progress.json，Git 工作区干净。按规范从 top4_loop07 开始，已通读其全部 272 行。定位依据仅为允许输入中的 citation、rationale、context 和 guideline，没有调用网络或模型 API，没有读取 LOG.md、PROGRESS.md、金标结果、既有归因或其他禁止材料。规范明确要求的进度和本次生成的定位输出只用于恢复、保存与检查。

已建立 check_quotes.py 和批次保存工具 write_batch.py。保存工具只序列化人工选定的引文及 citation 片段索引，不执行文本定位。每批按文件顺序处理 20 条并保存 progress.json。

第 1 至 2 批，共 40 条，增量检查通过，cannot_locate 为 0。第二批首次检查出现 5 个引文校验错误，涉及第 22、23、39、40 条。证据是引文中的弯引号和 § 被 PowerShell 管道编码转换成问号。重新读取 guideline 第 38、129、138、209 至 210、262 行后，按原人工选定的行复制原文并修正，复查通过。后续新增引文使用人工选定的行或保留 Unicode 的写入方式。

Phase 3 尚未开始，只有全部 11 份 guideline 的 Phase 1 和 Phase 2 完成后才能开始。Part B 尚未开始。

### top4_loop07 完成记录

按文件顺序完成全部 14 批，最后一批 19 条，共 279 条 located，cannot_locate 为 0。每批均已保存定位文件和 progress.json。所有已读 context 均包含相应预测文本，没有触发规范中的停止条件。输入目录的 36 个文件与 manifest 中的 SHA256 全部一致，只验证了允许输入副本，未读取其外部来源文件。

完整引文检查通过。检查器额外检查分号分隔的 citation 片段是否已记载或有 note 解释。该检查首次发现第 64 条的括号内分号产生第二片段，原记录未单独交代。重读该条允许输入后，在 note 中说明第二片段指向同一 gene/protein designation 规则，完整检查再次通过。

Phase 2 完成：58 个不同 basis 条目归并为 66 个 item，其中 12 个是连接分支用的合成父项。父项没有虚构的 quote_to_item 映射。已检查 item 原文、条件子串、父项链接、不同位置 restates 的相互链接，以及全部 58 个引文恰好映射一次。

对上下文规则、gene/protein 规则、患者自身条件、phenotypic 重述、§1a 排除分支和非首位修饰语排除分支的人工归并进行了独立只读复核，未发现明确违反归并规则的情况。第 196 行没有本次 basis 引文，因此没有为其额外创建重述 item。top4_loop07_merge_decisions.json 保留人工分配关系及排除分支的动作说明；other 不意味着直接赋予 O。

只读协作代理均限制在同一 Codex 任务内，读取范围仅为规范和允许输入，不使用其他 AI 工具、网络、API 或外部结果。保存、进度、校验和 Git 操作由主代理执行。
