import os
import  shutil

target_dir=r"D:\ceshi"     #目标文件夹

file_type_rule = {
    # 图片
    (".jpg", ".png", ".jpeg", ".gif", ".bmp", ".webp"): "图片",
    # 文档
    (".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls", ".ppt"): "文档",
    # 视频
    (".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"): "视频",
    # 音乐
    (".mp3", ".wav", ".flac", ".ogg"): "音乐",
    # 压缩包
    (".zip", ".rar", ".7z", ".tar", ".gz"): "压缩包",
    # 程序软件
    (".exe", ".bat", ".cmd"): "程序",
    # 图片设计文件
    (".psd", ".ai"): "设计文件"
}                           #文件类型规则

for file_name in os.listdir(target_dir):#遍历文件
    full_path=os.path.join(target_dir,file_name)     #获取文件路径
    if os.path.isdir(full_path):#判断是否是文件夹
        continue

    file_ext=os.path.splitext(file_name)[1].lower()#获取文件后缀

    category="其他文件"
    for exts,folder in file_type_rule.items():#遍历字典
        if file_ext in exts:#判断文件后缀
            category=file_type_rule[exts]#获取分类
            break
    category_path=os.path.join(target_dir,category)  #创建分类文件夹
    if not os.path.exists(category_path):#判断文件夹是否存在
        os.mkdir(category_path)     #创建文件夹

    new_path=os.path.join(category_path,file_name)#创建文件路径
    shutil.move(full_path,new_path)
    print(f"{file_name}移动到{category}")

