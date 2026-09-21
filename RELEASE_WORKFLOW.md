```bash
# ════════════════速查表══════════════════
git branch                         
git add -A && git status
git commit -m "<Version>: <desc>"
git push origin main
# 编辑 CITATION.cff version → <Version>, DOI → pending
git add CITATION.cff
git commit -m "bump CITATION.cff to <Version> (DOI pending)"
git push origin main
git tag -a <Version> -m "<Version>: <desc>"
git push origin <Version>
# → GitHub 发 Release → 等 Zenodo → 回填 DOI → commit & push

# ═══════════════════════════════════════════
# 阶段一：开发完成，推 main
# ═══════════════════════════════════════════

# 1. 确认在 main 分支
git branch
# 如果不在：git checkout main && git pull origin main

# 2. 提交所有改动
git add -A
git status                    # 确认要提交的文件列表
git commit -m "<Version>: <一句话描述这次改了什么>"

# 3. 推到 GitHub
git push origin main

# ═══════════════════════════════════════════
# 阶段二：更新 CITATION.cff 版本号（DOI 先留空或写旧值）
# ═══════════════════════════════════════════

# 4. 编辑 CITATION.cff：
#    - version: 改为 <Version>
#    - identifiers: concept DOI 写已知的（如果没变就沿用旧值），version DOI 写 "pending"
#    示例：
#      - description: "Version DOI (<Version>)"
#        type: doi
#        value: "pending"

git add CITATION.cff
git commit -m "bump CITATION.cff to <Version> (DOI pending)"
git push origin main

# ═══════════════════════════════════════════
# 阶段三：打 tag + 发 GitHub Release
# ═══════════════════════════════════════════

# 5. 打附注 tag（推荐 -a，有 tag message）
git tag -a <Version> -m "<Version>: <简短描述>"

# 6. 推 tag 到 GitHub（Zenodo 从这里开始监听）
git push origin <Version>

# 7. 去 GitHub 页面 → Releases → Draft a new release
#    - Choose tag: <Version>
#    - Title: <Version> — <描述>
#    - Description: 粘贴 Release notes
#    - ✅ Set as latest release
#    - ❌ Pre-release 不要勾
#    - 点 Publish

# ═══════════════════════════════════════════
# 阶段四：等 Zenodo 生成 DOI → 回填
# ═══════════════════════════════════════════

# 8. 等 2~5 分钟，打开 Zenodo → Account → GitHub
#    找到 <Version> record → 复制两个 DOI：
#    - Concept DOI（右侧 "Cite all versions"）
#    - Version DOI（页面顶部显示的那个）

# 9. 编辑 CITATION.cff，填入真实 DOI：
#      - description: "Concept DOI (all versions)"
#        value: "10.5281/zenodo.XXXXXXX"     # 填真实值
#      - description: "Version DOI (<Version>)"
#        value: "10.5281/zenodo.YYYYYYY"     # 填真实值

git add CITATION.cff
git commit -m "backfill Zenodo DOI for <Version>"
git push origin main

# ═══════════════════════════════════════════
# 阶段五（可选）：编辑 GitHub Release notes 加上 DOI
# ═══════════════════════════════════════════

# 10. GitHub Release 页面 → Edit release → 在 notes 顶部或底部加上：
#     **Zenodo DOI:** 10.5281/zenodo.YYYYYYY
#     **Concept DOI:** 10.5281/zenodo.XXXXXXX
#     Save changes

# 完毕。不打新 tag，不删旧 tag。
```