# -*- coding: utf-8 -*-
import os
import shutil
import random
import asyncio
import sqlite3
import telebot
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
path_to_extension: str = os.path.join(str(script_path).replace(r"\main.py", "\\MetaMask"))

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
	"""Получает ID расширения MetaMask"""
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

	return extension_id_by_name.get("MetaMask")

async def full_wallet_setup(page: Page, context: BrowserContext, seed_phrase: list, private_key: str, extension_id: str):
	"""Полная авторизация в кошельке MetaMask"""
	len_seed: int = len(seed_phrase)
	password: str = "12345678"

	await page.goto(
		url = f"chrome-extension://{extension_id}/home.html#onboarding/welcome"
	)

	await human_delay(1, 2.5)

	if len(context.pages) > 2:
		page_to_close = context.pages[2]
		print(f"[INFO] {datetime.now()} Закрываю:", page_to_close.url)
		await page_to_close.close()

	page = context.pages[1]

	await page.get_by_test_id("onboarding-terms-checkbox").click()
	await page.get_by_test_id("onboarding-import-wallet").click()
	await page.get_by_test_id("metametrics-no-thanks").click()

	if len_seed != 12:
		dropdown: str = page.locator(".dropdown__select").nth(1)
		await dropdown.select_option(value = str(len_seed))

	for idx, word in enumerate(seed_phrase):
		await page.get_by_test_id(f"import-srp__srp-word-{idx}").fill(word)

	await page.get_by_test_id("import-srp-confirm").click()

	for test_id in ("create-password-new", "create-password-confirm"):
		await page.get_by_test_id(test_id).fill(password)

	await page.get_by_test_id("create-password-terms").click()
	await page.get_by_test_id("create-password-import").click()
	await page.get_by_test_id("onboarding-complete-done").click()
	await page.get_by_test_id("pin-extension-next").click()
	await page.get_by_test_id("pin-extension-done").click()

	await page.goto(
		url = f"chrome-extension://{extension_id}/home.html"
	)

	try:
		await page.get_by_test_id("unlock-password").fill("12345678")
		await page.get_by_test_id("unlock-submit").click()
	except:pass

	try:await page.get_by_test_id("account-menu-icon").click()
	except:await page.get_by_text("Account 1").click()

	await page.get_by_test_id("multichain-account-menu-popover-action-button").click()
	await page.get_by_test_id("multichain-account-menu-popover-add-imported-account").click()
	await page.locator("#private-key-box").fill(private_key)
	await page.get_by_test_id("import-account-confirm-button").click()

	print(f"[INFO] {datetime.now()} Кошелек успешно настроен!")

async def connect_to_bytenova(context: BrowserContext, extension_id: str):
	bytenova_page: Page = await context.new_page()
	mt_page: str | None = None

	await bytenova_page.goto(
		url = "https://bytenova.ai/"
	)
	await human_delay(3.0, 5.0)
	await phantom_scroll(bytenova_page, 3)

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
		try:await mt_page.get_by_test_id("confirm-btn").click()
		except:pass
		try:await mt_page.get_by_test_id('confirmation-submit-button').click()
		except:
			try:await mt_page.get_by_text("Одобрить").click()
			except:pass
		try:await mt_page.get_by_test_id("confirm-footer-button").click()
		except:await mt_page.get_by_text("Подтвердить").click()
	try:
		create_btn: str = bytenova_page.get_by_text('Create a new account').first
		if await create_btn.is_visible():await create_btn.click()
		print(f"[INFO] {datetime.now()} Аккаунт создан!")
	except:pass
	await bytenova_page.close()

async def auto_daily_checkin(ip: str, page: Page, context: BrowserContext, extension_id: str):
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

			for _ in range(10):
				for _page in context.pages:
					url: str = _page.url
					if "notification.html" in url and extension_id in url:
						mt_page: str = _page
						break
				if mt_page:break
				await asyncio.sleep(1)

			if mt_page:
				print(f"[INFO] {datetime.now()} НАШЕЛ ДЕНЬ: {day}!")
				try:await mt_page.get_by_text("Подтвердить").click();await human_delay(1, 2)
				except:pass
				try:await mt_page.get_by_text("Confirm").click();await human_delay(1, 2)
				except:pass
				try:await mt_page.get_by_test_id("confirm-footer-button").click();await human_delay(2, 3)
				except:pass

				success += 1
				DB: sqlite3.Connection = sqlite3.connect(
					f"servers.db",
					check_same_thread = False
				)
				CURSOR: sqlite3.Cursor = DB.cursor()

				CURSOR.execute(f"UPDATE SERVERS set DAY{day} = ? WHERE ip = ?", ("True", ip));DB.commit()
				DB.close()
			else:
				errors += 1
				print(f"[INFO] {datetime.now()}")
		except:errors += 1

async def run(ip: str, seed_phrase: list, private_key: str, playwright: Playwright):
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
		seed_phrase = seed_phrase,
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
	shutil.rmtree(data_dir, ignore_errors=True)

async def main(ip: str, seed_phrase: str, private_key: str):
	"""Стартер раннера"""
	async with async_playwright() as p:
		await run(ip, seed_phrase.split(), private_key, p)

if __name__ == '__main__':
	DB: sqlite3.Connection = sqlite3.connect(
		"servers.db",
		check_same_thread = False
	)
	CURSOR: sqlite3.Cursor = DB.cursor()
	ARRAY: list = []

	for data in CURSOR.execute(f"SELECT * FROM SERVERS WHERE BYTENOVA = 'True'"):
		ip: str = data[0]
		notebook: str = data[1]
		seed_phrase: str = data[2]
		private_key: str = data[3]
		ARRAY.append(f"{ip}:{notebook}:{seed_phrase}:{private_key}")
	DB.close()

	for data in ARRAY:asyncio.run(main(data.split(":")[0], data.split(":")[2], data.split(":")[3]))

	print(
		f"[INFO] {datetime.now()} ВЫПОЛНИЛ: {success}\nОШИБОК: {errors}"
	)
