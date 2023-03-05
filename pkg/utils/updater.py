import datetime
import logging
import os.path

import requests
import json

import pkg.utils.context


def check_dulwich_closure():
    try:
        import pkg.utils.pkgmgr
        pkg.utils.pkgmgr.ensure_dulwich()
    except:
        pass

    try:
        import dulwich
    except ModuleNotFoundError:
        raise Exception("dulwich模块未安装,请查看 https://github.com/RockChinQ/QChatGPT/issues/77")


def pull_latest(repo_path: str) -> bool:
    """拉取最新代码"""
    check_dulwich_closure()

    from dulwich import porcelain

    repo = porcelain.open_repo(repo_path)
    porcelain.pull(repo)

    return True


def update_all() -> bool:
    """检查更新并下载源码"""
    current_tag = "v0.1.0"
    if os.path.exists("current_tag"):
        with open("current_tag", "r") as f:
            current_tag = f.read()

    rls_list_resp = requests.get(
        url="https://api.github.com/repos/RockChinQ/QChatGPT/releases"
    )

    rls_list = rls_list_resp.json()

    latest_rls = {}
    rls_notes = []
    for rls in rls_list:
        rls_notes.append(rls['name'])  # 使用发行名称作为note
        if rls['tag_name'] == current_tag:
            break

        if latest_rls == {}:
            latest_rls = rls
    logging.info("更新日志: {}".format(rls_notes))
    if latest_rls == {}:  # 没有新版本
        return False

    # 下载最新版本的zip到temp目录
    logging.info("开始下载最新版本: {}".format(latest_rls['zipball_url']))
    zip_url = latest_rls['zipball_url']
    zip_resp = requests.get(url=zip_url)
    zip_data = zip_resp.content

    # 检查temp/updater目录
    if not os.path.exists("temp"):
        os.mkdir("temp")
    if not os.path.exists("temp/updater"):
        os.mkdir("temp/updater")
    with open("temp/updater/{}.zip".format(latest_rls['tag_name']), "wb") as f:
        f.write(zip_data)

    logging.info("下载最新版本完成: {}".format("temp/updater/{}.zip".format(latest_rls['tag_name'])))

    # 解压zip到temp/updater/<tag_name>/
    import zipfile
    # 检查目标文件夹
    if os.path.exists("temp/updater/{}".format(latest_rls['tag_name'])):
        import shutil
        shutil.rmtree("temp/updater/{}".format(latest_rls['tag_name']))
    os.mkdir("temp/updater/{}".format(latest_rls['tag_name']))
    with zipfile.ZipFile("temp/updater/{}.zip".format(latest_rls['tag_name']), 'r') as zip_ref:
        zip_ref.extractall("temp/updater/{}".format(latest_rls['tag_name']))

    # 覆盖源码
    source_root = ""
    # 找到temp/updater/<tag_name>/中的第一个子目录路径
    for root, dirs, files in os.walk("temp/updater/{}".format(latest_rls['tag_name'])):
        if root != "temp/updater/{}".format(latest_rls['tag_name']):
            source_root = root
            break

    # 覆盖源码
    import shutil
    for root, dirs, files in os.walk(source_root):
        # 覆盖所有子文件子目录
        for file in files:
            src = os.path.join(root, file)
            dst = src.replace(source_root, ".")
            if os.path.exists(dst):
                os.remove(dst)
            shutil.copy(src, dst)

    # 把current_tag写入文件
    current_tag = latest_rls['tag_name']
    with open("current_tag", "w") as f:
        f.write(current_tag)

    # 通知管理员
    import pkg.utils.context
    pkg.utils.context.get_qqbot_manager().notify_admin("已更新到最新版本: {}\n更新日志:\n{}\n新功能通常可以在config-template.py中看到，完整的更新日志请前往 https://github.com/RockChinQ/QChatGPT/releases 查看".format(current_tag, "\n".join(rls_notes)))
    return True


def is_repo(path: str) -> bool:
    """检查是否是git仓库"""
    check_dulwich_closure()

    from dulwich import porcelain
    try:
        porcelain.open_repo(path)
        return True
    except:
        return False


def get_remote_url(repo_path: str) -> str:
    """获取远程仓库地址"""
    check_dulwich_closure()

    from dulwich import porcelain
    repo = porcelain.open_repo(repo_path)
    return str(porcelain.get_remote_repo(repo, "origin")[1])


def get_current_version_info() -> str:
    """获取当前版本信息"""
    check_dulwich_closure()

    from dulwich import porcelain

    repo = porcelain.open_repo('.')

    version_str = ""

    for entry in repo.get_walker():
        version_str += "提交编号: "+str(entry.commit.id)[2:9] + "\n"
        tz = datetime.timezone(datetime.timedelta(hours=entry.commit.commit_timezone // 3600))
        dt = datetime.datetime.fromtimestamp(entry.commit.commit_time, tz)
        version_str += "时间: "+dt.strftime('%m-%d %H:%M:%S') + "\n"
        version_str += "说明: "+str(entry.commit.message, encoding="utf-8").strip() + "\n"
        version_str += "提交作者: '" + str(entry.commit.author)[2:-1] + "'"
        break

    return version_str


def get_commit_id_and_time_and_msg() -> str:
    """获取当前提交id和时间和提交信息"""
    check_dulwich_closure()

    from dulwich import porcelain

    repo = porcelain.open_repo('.')

    for entry in repo.get_walker():
        tz = datetime.timezone(datetime.timedelta(hours=entry.commit.commit_timezone // 3600))
        dt = datetime.datetime.fromtimestamp(entry.commit.commit_time, tz)
        return str(entry.commit.id)[2:9] + " " + dt.strftime('%Y-%m-%d %H:%M:%S') + " [" + str(entry.commit.message, encoding="utf-8").strip()+"]"


def get_current_commit_id() -> str:
    """检查是否有新版本"""
    check_dulwich_closure()

    from dulwich import porcelain

    repo = porcelain.open_repo('.')
    current_commit_id = ""
    for entry in repo.get_walker():
        current_commit_id = str(entry.commit.id)[2:-1]
        break

    return current_commit_id


def is_new_version_available() -> bool:
    """检查是否有新版本"""
    check_dulwich_closure()

    from dulwich import porcelain

    repo = porcelain.open_repo('.')
    fetch_res = porcelain.ls_remote(porcelain.get_remote_repo(repo, "origin")[1])

    current_commit_id = get_current_commit_id()

    latest_commit_id = str(fetch_res[b'HEAD'])[2:-1]

    return current_commit_id != latest_commit_id


if __name__ == "__main__":
    update_all()
