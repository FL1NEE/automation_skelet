# -*- coding: utf-8 -*-
import os
import shutil
import random
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime
from playwright.async_api import Page
from playwright.async_api import Playwright
from playwright.async_api import BrowserContext
from playwright.async_api import async_playwright

def get_user_data_dir():
	"""Генератор рандомных директорий"""
	return f"/tmp/test-user-data-dir-{random.randint(1, 10000000000)}"

errors: int = 0
success: int = 0
script_path: str = os.path.abspath(__file__)
path_to_extension: str = os.path.join(str(script_path).replace(r"\main.py", "\\Rabby"))

async def human_delay(min_seconds: float = 0.5, max_seconds: float = 2.0):
	"""Случайные задержки для имитации человеческого поведения"""
	delay: float = random.uniform(min_seconds, max_seconds) / 2
	await asyncio.sleep(delay)

async def phantom_scroll(page: Page, scroll_count: int = 5):
	"""Фантомные прокруты страницы для имитации человеческого поведения"""
	if page.url.startswith("chrome-extension://"):
		return

	for _ in range(scroll_count):
		scroll_direction: str = random.choice([-1, 1])
		scroll_amount: int = random.randint(100, 500) * scroll_direction
		await page.mouse.wheel(0, scroll_amount)
		await human_delay(0.3, 1.0)

	await human_delay(0.5, 1.5)

async def get_extension_id(page: Page) -> str:
	"""Получает ID расширения Rabby"""
	await page.goto("chrome://extensions")
	extension_id_by_name: dict = {}

	card_elements: list = await page.query_selector_all("div#card")
	for card in card_elements:
		name_el: list = await card.query_selector("div#name")
		name: str = (await name_el.text_content()).replace("\n", "").replace(" ", "")

		details_btn: str = await card.query_selector("cr-button#detailsButton")
		async with page.expect_navigation():
			await details_btn.click()

		extension_id: str = page.url.split("?id=")[-1]
		extension_id_by_name[name] = extension_id

		back_btn: str = await page.query_selector("cr-icon-button#closeButton")
		async with page.expect_navigation():
			await back_btn.click()

	return extension_id_by_name.get("RabbyWallet")

async def full_wallet_setup(page: Page, context: BrowserContext, private_key: str, extension_id: str):
	"""Полная авторизация в кошельке RabbyWallet"""
	password: str = "12345678"

	await page.goto(
		url = f"chrome-extension://{extension_id}/index.html#/new-user/guide"
	)

	if len(context.pages) > 2:
		page_to_close = context.pages[2]
		print(f"[INFO] {datetime.now()} Закрываю:", page_to_close.url)
		await page_to_close.close()

	page: Page = context.pages[1]

	await page.get_by_text("I already have an address").click()

	await page.get_by_text("Private Key").click()

	await page.locator("#privateKey").fill(private_key)
	await page.get_by_text("Confirm").click()

	await page.locator("#password").fill(password)
	await page.locator("#confirmPassword").fill(password)
	try:await page.get_by_text("Confirm").click()
	except:pass
	try:await page.get_by_text("Get Started").click()
	except:pass
	try:await page.get_by_text("Done").click()
	except:pass
	print(f"[INFO] {datetime.now()} АВТОРИЗАЦИЯ В RABBY WALLET ПРОЙДЕНА!")

async def wallet_login(page: Page, rabby_extension_id: str):
	""""""
	await page.goto(
		url = f"chrome-extension://{rabby_extension_id}/popup.html"
	)
	await page.locator("#password").fill("12345678")
	await page.get_by_text("Unlock").click()
	print("[INFO] СОВЕРШИЛ ВХОД В КОШЕЛЕК")

async def sign_rabby(context: BrowserContext, extension_id: str):
	rabby_page: str | None = None
	for _page in context.pages:
		url: str = _page.url
		if f"{extension_id}/notification.html" in url:
			rabby_page: str = _page
			break

	if rabby_page:
		try:await rabby_page.get_by_role("button", name="Sign").click()
		except:pass
		try:await rabby_page.get_by_role("button", name="Confirm").click()
		except:pass

async def connect_to_bytenova(context: BrowserContext, extension_id: str):
	bytenova_page: Page = await context.new_page()
	mt_page: str | None = None

	await bytenova_page.goto(
		url = "https://bytenova.ai/"
	)
	await human_delay(3.0, 5.0)
	await phantom_scroll(bytenova_page, 3)

	try:
		data: str = bytenova_page.get_by_text("Login").first
		await data.click()
		await human_delay(1.0, 2.0)
	except:pass


	try:
		data: str = bytenova_page.get_by_text("Connect Wallet").first
		await data.click()
		await human_delay(1.0, 2.0)
	except:pass
	try:
		data: str = bytenova_page.get_by_text("MetaMask", exact = True).first
		await data.click()
		await human_delay(2.0, 3.0)
	except:pass

	for _page in context.pages:
		url: str = _page.url
		if ('notification.html' in url or 'popup.html' in url) and extension_id in url:
			mt_page: str = _page
			break

	if mt_page:
		try:
			connection = mt_page.get_by_text("Connect").nth(2)
			await connection.click()
			await asyncio.sleep(2)
			await sign_rabby(context, extension_id)
		except:pass
	await asyncio.sleep(2)
	try:await sign_rabby(context, extension_id)
	except:pass
	try:
		create_btn: str = bytenova_page.get_by_text('Create a new account').first
		if await create_btn.is_visible():await create_btn.click()
		print(f"[INFO] {datetime.now()} Аккаунт создан!")
	except:pass
	await bytenova_page.close()

async def auto_daily_checkin(ip: str, page: Page, extension_id: str, context: BrowserContext):
	"""Выполнение Daily Check-In в проекте Bytenova"""
	global errors, success
	mt_page: str | None = None
	bytenova_page: str = await context.new_page()
	await bytenova_page.goto(
		url = f"https://bytenova.ai/rewards/quests"
	)

	await human_delay(1.0, 1.2)

	await bytenova_page.get_by_text("DAILY").click()

	for day in range(1, 8):
		try:
			btn_text: str = f"Day {day} Check-In"

			btn: str = bytenova_page.get_by_text(btn_text).first

			if not await btn.is_visible():continue
      
			await btn.click()
			await human_delay(1.0, 1.5)

			try:
				await sign_rabby(context, extension_id)
				success += 1
				DB: sqlite3.Connection = sqlite3.connect(
					f"servers.db",
					check_same_thread = False
				)
				CURSOR: sqlite3.Cursor = DB.cursor()

				CURSOR.execute(f"UPDATE SERVERS set DAY{day} = ? WHERE IP = ?", ("True", ip));DB.commit()
				DB.close()
			except:
				errors += 1
				print(f"[INFO] {datetime.now()} Не удалось выполнить ")
		except:errors += 1

async def run(ip: str, private_key: str, playwright: Playwright):
	"""Раннер для выполнения круга"""
	data_dir: str = get_user_data_dir()
	context: BrowserContext = await playwright.chromium.launch_persistent_context(
		data_dir,
		headless = False,
		args = \
		[
			f"--disable-extensions-except={path_to_extension}",
			f"--load-extension={path_to_extension}"
		]
	)

	page: Page = await context.new_page()
	extension_id: str = await get_extension_id(page)

	await full_wallet_setup(
		page = page,
		context = context,
		private_key = private_key,
		extension_id = extension_id
	)

	await connect_to_bytenova(
		context = context,
		extension_id = extension_id
	)
	page: Page = await context.new_page()

	await auto_daily_checkin(
		ip = ip,
		page = page,
		context = context,
		extension_id = extension_id
	)

	await context.close()
	print(f"[INFO] {datetime.now()} Сервер: {ip} выполнил таск!")
	shutil.rmtree(data_dir, ignore_errors = True)

async def main(ip: str, private_key: str):
	"""Стартер раннера"""
	async with async_playwright() as p:
		await run(ip, private_key, p)

if __name__ == '__main__':
	DB: sqlite3.Connection = sqlite3.connect(
		"SERVERS.db",
		check_same_thread = False
	)
	CURSOR: sqlite3.Cursor = DB.cursor()
	ARRAY: list = []

	for data in CURSOR.execute(f"SELECT * FROM SERVERS WHERE BYTENOVA = 'True'"):
		ip: str = data[0]
		notebook: str = data[1]
		private_key: str = data[2]
		ARRAY.append(f"{ip}:{notebook}:{private_key}")
	DB.close()

	for data in ARRAY:
		try:asyncio.run(main(data.split(":")[0], data.split(":")[2]))
		except:pass
	ARRAY.clear()
	DB: sqlite3.connection(
		"servers.db",
		check_same_thread = False
	)
	for data in CURSOR.execute(f"SELECT * FROM SERVERS WHERE BYTENOVA = 'True'"):
		ip: str = data[0]
		notebook: str = data[1]
		private_key: str = data[2]
		ARRAY.append(f"{ip}:{notebook}:{private_key}")
	DB.close()

	print(
		f"[INFO] {datetime.now()} ВЫПОЛНИЛ: {success}\nОШИБОК: {errors}"
	)
