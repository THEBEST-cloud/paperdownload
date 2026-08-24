# 安装与配置

## 安装 Skill

从 GitHub 仓库生成脱敏、自包含的 Skill 目录：

```bash
git clone --depth 1 https://github.com/THEBEST-cloud/paperdownload.git
cd paperdownload

# Codex（二选一）
python3 scripts/make_skill.py "${CODEX_HOME:-$HOME/.codex}/skills/paperdl"

# Claude Code（二选一）
python3 scripts/make_skill.py "$HOME/.claude/skills/paperdl"
```

重启 Codex 或 Claude Code，使新 Skill 被发现。直接收到别人生成好的
`paperdl/` 目录时，将整个目录放到上述对应位置即可。

## 安装运行环境

以下以 Codex 默认目录为例；Claude Code 请替换 `PAPERDL_SKILL`：

```bash
PAPERDL_SKILL="${CODEX_HOME:-$HOME/.codex}/skills/paperdl"
bash "$PAPERDL_SKILL/app/scripts/setup.sh"
```

脚本需要 Python 3.10+ 和网络，并会在 `app/.venv` 安装 Python 依赖及
patchright Chromium。无图形界面的 Linux 服务器还需安装 Xvfb。

## 配置账号

把用户数据放在 Skill 目录之外，避免升级 Skill 时覆盖凭据和下载文件：

```bash
PAPERDL_SKILL="${CODEX_HOME:-$HOME/.codex}/skills/paperdl"
PAPERDL="$PAPERDL_SKILL/app/.venv/bin/paperdl"
mkdir -p "$HOME/paperdl-data"
cd "$HOME/paperdl-data"

"$PAPERDL" config
"$PAPERDL" doctor
"$PAPERDL" login
```

`config` 将在当前目录生成权限为 `600` 的 `.paperdl.env`。机构订阅下载
必须填写：

- `CSTCLOUD_ID`：登录中国科技云通行证使用的中科院邮箱账号。
- `CSTCLOUD_PASSWORD`：通行证密码，输入时不回显。

其余配置均可留空：

- `ELSEVIER_API_KEY`、`ELSEVIER_INSTTOKEN`：Elsevier 官方接口加速。
- `WILEY_TDM_TOKEN`：Wiley TDM 接口加速。
- `OPENALEX_MAILTO`：OpenAlex 礼貌池邮箱；留空时回退到通行证账号。
- `SMTP_*`：仅在网页端发送 PDF 邮件时需要。

也可在数据目录手工配置：

```bash
cp "$PAPERDL_SKILL/references/env.example" .paperdl.env
chmod 600 .paperdl.env
```

不要提交或分享 `.paperdl.env` 与 `.profile/`。

## 使用

后续都从同一数据目录运行：

```bash
"$PAPERDL" search "microplastics drinking water" --from 2020 -n 25
"$PAPERDL" run dois.txt
"$PAPERDL" retry
"$PAPERDL" serve --host 0.0.0.0 --port 8200
```

OpenAlex 检索无需机构登录；订阅全文下载需要先完成 `login`。能否取得
全文取决于机构订阅范围。
