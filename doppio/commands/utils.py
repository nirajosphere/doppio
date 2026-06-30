import re
import json
import subprocess
from pathlib import Path


def create_file(path: Path, content: str | None = None):
	# Create the file if not exists
	if not path.exists():
		path.touch()

	# Write the contents (if any)
	if content:
		with path.open("w") as f:
			f.write(content)


def _append_command(existing: str | None, new_cmd: str) -> str:
	if not existing:
		return new_cmd
	if new_cmd in existing:
		return existing
	return f"{existing} && {new_cmd}"


def add_commands_to_root_package_json(app, spa_name):
	app_path = Path("../apps") / app
	spa_path: Path = app_path / spa_name
	package_json_path: Path = spa_path / "package.json"

	if not package_json_path.exists():
		print("package.json not found. Please manually update the build command.")
		return


	with package_json_path.open("r") as f:
		data = json.load(f)

	data["scripts"][
		"build"
	] = f"vite build --base=/assets/{app}/{spa_name}/ && yarn copy-html-entry"

	data["scripts"]["copy-html-entry"] = (
		f"cp ../{app}/public/{spa_name}/index.html" f" ../{app}/www/{spa_name}.html"
	)

	with package_json_path.open("w") as f:
		json.dump(data, f, indent=2)

	app_package_json_path: Path = app_path / "package.json"

	if not app_package_json_path.exists():
		subprocess.run(["npm", "init", "--yes"], cwd=app_path)

	with app_package_json_path.open("r") as f:
		app_data = json.load(f)

	app_data.setdefault("scripts", {})
	scripts = app_data["scripts"]

	scripts["postinstall"] = _append_command(
		scripts.get("postinstall"), f"cd {spa_name} && yarn install"
	)

	scripts["build"] = _append_command(
		scripts.get("build"), f"cd {spa_name} && yarn build"
	)

	with app_package_json_path.open("w") as f:
		json.dump(app_data, f, indent=2)


def add_routing_rule_to_hooks(app, spa_name):
	hooks_py = Path(f"../apps/{app}/{app}") / "hooks.py"
	hooks = ""
	with hooks_py.open("r") as f:
		hooks = f.read()

	pattern = re.compile(r"website_route_rules\s?=\s?\[(.+)\]")

	rule = (
		"{" + f"'from_route': '/{spa_name}/<path:app_path>', 'to_route': '{spa_name}'" + "}"
	)

	rules = pattern.sub(r"website_route_rules = [{rule}, \1]", hooks)

	# If rule is not already defined
	if not pattern.search(hooks):
		rules = hooks + "\nwebsite_route_rules = [{rule},]"

	updates_hooks = rules.replace("{rule}", rule)
	with hooks_py.open("w") as f:
		f.write(updates_hooks)
