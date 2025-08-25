# -*- coding: utf-8 -*-
import os
import random
import asyncio
import sqlite3
import telebot
from pathlib import Path
from datetime import datetime
from playwright.async_api import Page, Playwright, async_playwright

def get_user_data_dir():
	return f"/tmp/test-user-data-dir-{random.randint(1, 10000000000)}"

script_path: str = os.path.abspath(__file__)
path_to_extension: str = os.path.join(str(script_path).replace(r"\main.py", "\\MetaMask"))

async def human_delay(min_seconds: float = 0.5, max_seconds: float = 2.0):
	"""Случайные задержки для имитации человеческого поведения"""
	delay: float = random.uniform(min_seconds, max_seconds)
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

	await page.keyboard.press("home")
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
		extension_id_by_name[name]: str = extension_id

		back_btn: str = await page.query_selector("cr-icon-button#closeButton")
		async with page.expect_navigation():
			await back_btn.click()


	return extension_id_by_name.get("MetaMask")# or RabbyWallet

async def full_wallet_setup(page: Page, seed_phrase: list, private_key: str, extension_id: str):
	"""Полная авторизация в кошельке MetaMask"""
	len_seed: int = len(seed_phrase)
	password: str = "12345678"

	await page.goto(
		url = f"chrome-extension://{extension_id}/home.html#onboarding/welcome"
	)

	await page.get_by_test_id("onboarding-terms-checkbox").click()
	await page.get_by_test_id("onboarding-import-wallet").click()
	await page.get_by_test_id("metametrics-no-thanks").click()

	if len_seed != 12:
		dropdown: str = page.locator(".dropdown__select").nth(1)
		await dropdown.select_option(value = str(len_seed))

	for idx, word in enumerate(seed_phrase):
		await page.get_by_test_id(f"import-srp__srp-word-{idx}").fill(word)
		await human_delay(0.1, 0.2)

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
	except:await page.get_by_text("Account 1")

	await page.get_by_test_id("multichain-account-menu-popover-action-button").click()
	await page.get_by_test_id("multichain-account-menu-popover-add-imported-account").click()
	await page.locator("#private-key-box").fill(private_key)
	await page.get_by_test_id("import-account-confirm-button").click()

	print(f"[INFO] {datetime.now()} Кошелек успешно настроен!")

async def connect_to_bytenova(context: str, extension_id: str):
	bytenova_page: str = await context.new_page()
	mt_page: str | None= None

	await bytenova_page.goto(
		url = "https://bytenova.ai/"
	)
	await human_delay(3.0, 5.0)
	await phantom_scroll(bytenova_page, 3)

	try:
		await bytenova_page.get_by_text("Connect Wallet").first.click()
		await human_delay(1.0, 2.0)
	except:pass
	try:
		await bytenova_page.get_by_text("MetaMask", exact=True).first.click()
        await human_delay(2.0, 3.0)
    except:pass

    for _page in context.pages:
    	url: str = _page.url
    	if ('notification.html' in url or 'popup.html' in url) and extension_id in url:
    		mt_page: str = _page
    		break

    if mt_page:
    	for selector in ["text=Одобрить", "text=Confirm", "test-id=confirm-btn"]:
    		try:
    			await mt_page.locator(selector.replace("text=", "")).click(timeout = 3000)
    			break
    		except:continue

    	try:await mt_page.get_by_test_id("confirm-footer-button").click()
    	except:pass

    # Создание аккаунта
    try:
        create_btn = bytenova_page.get_by_text('Create a new account').first
        if await create_btn.is_visible():
            await create_btn.click()
            print("Аккаунт создан")
    except:
        pass

    await bytenova_page.close()

# ✅ НОВАЯ ФУНКЦИЯ: Автоопределение дня
async def auto_daily_checkin(context, metamask_extension_id: str, ip: str):
    global success, error
    bytenova_page = await context.new_page()
    try:
        await bytenova_page.goto("https://bytenova.ai/rewards/quests")  # ✅ Без пробелов
        await human_delay(3.0, 5.0)
        await phantom_scroll(bytenova_page, 4)

        await bytenova_page.get_by_text('DAILY').first.click()
        await human_delay(1.5, 2.5)

        completed_up_to = 0

        for day in range(1, 8):
            btn_text = f"Day {day} Check-In"
            button = bytenova_page.get_by_text(btn_text).first

            if not await button.is_visible():
                continue

            print(f"Проверяем: {btn_text}")
            await button.click()
            await human_delay(1.0, 1.5)

            # Ожидаем MetaMask
            mt_page = None
            for _ in range(10):  # Ждём до 10 сек
                for page in context.pages:
                    url = page.url
                    if ('notification.html' in url or 'popup.html' in url) and metamask_extension_id in url:
                        mt_page = page
                        break
                if mt_page:
                    break
                await asyncio.sleep(1)

            if mt_page:
                print(f"✅ MetaMask появился при Day {day} → это следующий день!")
                completed_up_to = day

                # Подтверждение
                try: await mt_page.get_by_text("Подтвердить").click(); await human_delay(1, 2)
                except: pass
                try: await mt_page.get_by_text("Confirm").click(); await human_delay(1, 2)
                except: pass
                try: await mt_page.get_by_test_id("confirm-footer-button").click(); await human_delay(2, 3)
                except: pass

                # Отчёт
                await asyncio.to_thread(
                    BOT.send_message,
                    chat_id=CHAT_ID_1,
                    text=f"#BYTENOVA\n\n✅ <i><b>SUCCESS</b></i>\n\n<b>Сервер</b>: {ip}\n<b>ByteNova - Выполнен чекин до Day {day}</b>"
                )
                success += 1
                break  # Выход после успешного
            else:
                print(f"❌ MetaMask не появился → Day {day} уже выполнен")

        # Обновляем БД: все дни от 1 до completed_up_to = True
        if completed_up_to > 0:
            DB = sqlite3.connect("servers.db", check_same_thread=False)
            CURSOR = DB.cursor()
            for d in range(1, completed_up_to + 1):
                CURSOR.execute(f"UPDATE SERVERS SET DAY{d} = ? WHERE ip = ?", ("True", ip))
            DB.commit()
            DB.close()
        elif completed_up_to == 0:
            await asyncio.to_thread(
                BOT.send_message,
                chat_id=CHAT_ID_1,
                text=f"#BYTENOVA\n\nℹ️ <i><b>INFO</b></i>\n\n<b>Сервер</b>: {ip}\n<b>ByteNova - Все дни уже выполнены.</b>"
            )

    except Exception as e:
        print(f"Ошибка: {e}")
        error += 1
        await asyncio.to_thread(
            BOT.send_message,
            chat_id=CHAT_ID_1,
            text=f"#BYTENOVA\n\n❗️ <i><b>ERROR</b></i>\n\n<b>Сервер</b>: {ip}\n<b>Ошибка: {str(e)[:100]}...</b>"
        )
    finally:
        await bytenova_page.close()

async def run(playwright: Playwright, seed_phrase: list, private_key: str, ip: str):
    context = await playwright.chromium.launch_persistent_context(
        get_user_data_dir(),
        headless=False,
        args=[
            f"--disable-extensions-except={path_to_extension}",
            f"--load-extension={path_to_extension}",
        ]
    )

    page = await context.new_page()
    metamask_extension_id = await get_extension_id(page)

    await full_wallet_setup(page, metamask_extension_id, seed_phrase, private_key)
    await connect_to_bytenova(context, metamask_extension_id)
    
    # ✅ Заменено: автоматический чекин
    await auto_daily_checkin(context, metamask_extension_id, ip)

    await context.close()

async def main(seed_phrase: str, private_key: str, ip: str):
    async with async_playwright() as p:
        await run(p, seed_phrase.split(), private_key, ip)