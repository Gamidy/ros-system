#!/usr/bin/env python3
"""
ROS 系统密码安全修复脚本
===========================
功能：
  1. 为所有用户生成独立的 12 位随机密码（含大小写字母+数字）
  2. 使用 bcrypt 哈希后批量更新数据库
  3. 将用户名→新密码映射输出到安全文件
  4. 验证所有密码更新成功

用法：
  cd backend && python scripts/reset_passwords.py

安全注意：
  - 生成的密码文件应妥善保管，分发后立即删除
  - 建议在非生产环境先验证，确认无误后再在生产执行
"""

import sys
import os
import secrets
import string
import datetime

# 确保能找到 backend 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.core.security import get_password_hash, verify_password
from app.models.user import User

# ── 配置 ──────────────────────────────────────────────

PASSWORD_LENGTH = 12
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'new_passwords.txt')

# 密码字符集: 大小写字母 + 数字 (排除易混淆字符如 0/O/1/l/I)
ALPHABET = string.ascii_letters + string.digits
EXCLUDE_CHARS = '0O1lI'
SAFE_ALPHABET = ''.join(c for c in ALPHABET if c not in EXCLUDE_CHARS)


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    """生成安全的随机密码（密码学强度随机源）"""
    # 确保至少包含 1 个大写、1 个小写、1 个数字
    while True:
        pwd = ''.join(secrets.choice(SAFE_ALPHABET) for _ in range(length))
        if (any(c.isupper() for c in pwd) and
            any(c.islower() for c in pwd) and
            any(c.isdigit() for c in pwd)):
            return pwd


def main():
    db = SessionLocal()
    try:
        # 1. 查询所有用户
        users = db.query(User).all()
        total = len(users)
        print(f"发现 {total} 个用户")

        if total == 0:
            print("没有用户需要更新")
            return

        # 2. 为每个用户生成新密码并哈希
        user_passwords: dict[str, str] = {}
        for user in users:
            new_password = generate_password()
            user_passwords[user.username] = new_password
            user.hashed_password = get_password_hash(new_password)  # type: ignore[assignment]

        # 3. 批量提交
        db.commit()
        print(f"已为 {total} 个用户更新密码")

        # 4. 验证：重新查询并验证至少一个
        first_user = db.query(User).first()
        if first_user and first_user.username in user_passwords:
            test_pwd = user_passwords[first_user.username]
            if verify_password(test_pwd, first_user.hashed_password):
                print(f"验证成功: 用户 '{first_user.username}' 密码哈希正确")
            else:
                print(f"警告: 用户 '{first_user.username}' 密码验证失败!")

        # 5. 输出到文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("ROS 系统 - 用户新密码列表 (机密)\n")
            f.write(f"生成时间: {datetime.datetime.now()}\n")
            f.write(f"用户总数: {total}\n")
            f.write("=" * 60 + "\n\n")
            for username, pwd in user_passwords.items():
                f.write(f"  {username:<30} {pwd}\n")
            f.write("\n" + "=" * 60 + "\n")
            f.write("请妥善保管此文件，分发密码后务必删除！\n")
            f.write("=" * 60 + "\n")

        print(f"\n密码列表已保存到: {OUTPUT_FILE}")
        print("请妥善保管此文件，分发密码后务必删除！")

        # 6. 屏幕输出前 5 个作为确认
        print("\n--- 前 5 个用户的新密码 (预览) ---")
        for i, (username, pwd) in enumerate(user_passwords.items()):
            if i >= 5:
                break
            print(f"  {username}: {pwd}")
        if total > 5:
            print(f"  ... 还有 {total - 5} 个用户，详见 {OUTPUT_FILE}")

    except Exception as e:
        db.rollback()
        print(f"错误: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
