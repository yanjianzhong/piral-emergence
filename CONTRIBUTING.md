# Contributing to Spiral Emergence

感谢你考虑为七阶段涌现框架贡献代码或文档。

## 如何贡献

1. Fork 本仓库
2. 创建分支 (`git checkout -b feature/your-feature`)
3. 提交变更 (`git commit -s -m "描述你的修改"`)
4. 推送分支 (`git push origin feature/your-feature`)
5. 提交 Pull Request

## 签署 DCO（开发者原产地证书）

每个 commit **必须**包含 `Signed-off-by` 行，表明你同意 DCO：
```
bash
git commit -s -m "fix: 修复 N=17 扫描的边界条件"
这会生成：
Signed-off-by: 你的名字 <your.email@example.com>
```
**DCO 声明全文：**

> By making a contribution to this project, I certify that:
> 
> (a) The contribution was created in whole or in part by me and I have the
> right to submit it under the Apache License 2.0; or
> 
> (b) The contribution is based upon previous work that, to the best of my
> knowledge, is covered by an appropriate open source license and I have
> the right to submit that work with modifications, whether created in
> whole or in part by me, under the Apache License 2.0; or
> 
> (c) I have not modified the contribution and I am submitting it under the
> Apache License 2.0.
> 
> I understand and agree that this project and the contribution are public
> and that a record of the contribution (including all personal information
> I submit with it) is maintained indefinitely and may be redistributed
> consistent with this project or the open source license(s) involved.

## 轻量 CLA（贡献者许可协议）

除 DCO 外，你同意以下额外条款：

1. **专利许可**：你就本贡献所覆盖的任何专利，授予本项目永久、全球、免费、不可撤销的使用许可（与 Apache-2.0 第3条一致）。
2. **原创性声明**：你声明贡献不包含未经授权的第三方专利、版权或商业秘密。
3. **不主张商标**：你不以本项目名义使用任何商标或服务标记。

## 代码规范

- Python 代码遵循 PEP 8
- 新增数值实验需附带审计守卫（guard）和负对照说明
- 新增依赖需在 `requirements.txt` 中声明并注明用途
- 所有新文件头部注明版权年份和 Apache-2.0 许可引用

## 诚实边界

本项目的核心原则是"夯实模拟事实地基"。贡献的算法、数据或结论应：
- 标注证据成熟度（高/中/低）
- 包含负对照或失败情况说明
- 不夸大未经验证的物理/哲学结论

## 问题反馈

- Bug 报告：开 Issue，附复现步骤 + 环境信息
- 学术讨论：优先在 arXiv/Zenodo 评论区或知乎/CSDN 文章下交流
- 紧急联系：mohedanovinita984@gmail.com

---

再次感谢你的贡献。每一个 PR 都是对"可计算涌现"地基的加固。