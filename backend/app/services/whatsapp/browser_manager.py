"""
Browser management for WhatsApp Web automation
"""
import logging
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser instance and contexts"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
    
    async def initialize(self):
        """Initialize Playwright browser"""
        if self.playwright is None:
            logger.info("Starting Playwright...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            logger.info("Playwright started, browser launched (headless)")
    
    async def shutdown(self):
        """Shutdown browser and cleanup"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def create_persistent_context(
        self, 
        user_data_dir: str,
        viewport: Optional[dict] = None,
        user_agent: Optional[str] = None
    ) -> BrowserContext:
        """
        Create a persistent browser context
        
        Args:
            user_data_dir: Directory for browser data (cookies, storage, etc.)
            viewport: Viewport size (default: {'width': 1280, 'height': 720})
            user_agent: User agent string (default: Chrome on Linux)
        
        Returns:
            BrowserContext instance
        """
        await self.initialize()
        
        if viewport is None:
            viewport = {'width': 1280, 'height': 720}
        
        if user_agent is None:
            user_agent = (
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        
        context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            viewport=viewport,
            user_agent=user_agent,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ],
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )
        
        return context
    
    async def create_page(self, context: BrowserContext) -> Page:
        """
        Create or get a page from context with anti-detection settings
        
        Args:
            context: BrowserContext instance
        
        Returns:
            Page instance
        """
        # Get the first page from persistent context
        pages = context.pages
        if pages:
            page = pages[0]
        else:
            page = await context.new_page()
        
        # Override webdriver property to avoid detection
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return page
