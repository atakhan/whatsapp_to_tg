"""
Source selector - chooses the best available data source.
"""

from typing import Dict, Optional, Tuple
import logging

from playwright.async_api import Page

from .base import IChatSource, SourceUnavailableError
from .store_chat_source import StoreChatSource
from .cdp_network_chat_source import CDPNetworkChatSource
from .dom_chat_source import DOMChatSource

logger = logging.getLogger(__name__)


class SourceSelector:
    """
    Selects the optimal chat data source based on availability.
    
    Priority order:
    1. StoreChatSource (preferred - most reliable)
    2. CDPNetworkChatSource (alternative - reliable IDs)
    3. DOMChatSource (fallback - least reliable)
    """
    
    @staticmethod
    async def select_source(page: Page) -> Tuple[IChatSource, bool, Dict]:
        """
        Select the best available source.
        
        Args:
            page: Playwright page instance
            
        Returns:
            Tuple of (selected_source, is_degraded, metadata)
            - selected_source: The chosen IChatSource implementation
            - is_degraded: True if fallback source was used (not preferred)
            - metadata: Dictionary with selection information for diagnostics
        """
        metadata = {
            'attempted_sources': [],
            'selected_source': None,
            'selection_reason': None,
            'errors': []
        }
        
        # Try Store source first (preferred)
        try:
            logger.info("Attempting to use Store source (priority 1)...")
            metadata['attempted_sources'].append({
                'source': 'store',
                'priority': 1,
                'status': 'attempting'
            })
            
            store_source = StoreChatSource(page)
            await store_source.init()
            
            metadata['selected_source'] = 'store'
            metadata['selection_reason'] = 'Preferred source available'
            metadata['attempted_sources'][-1]['status'] = 'success'
            
            logger.info(
                "✓ Selected Store source (preferred) - total_count=%s",
                await store_source.total_expected()
            )
            return store_source, False, metadata
            
        except SourceUnavailableError as e:
            reason = str(e)
            logger.warning("Store source unavailable: %s", reason)
            metadata['attempted_sources'][-1]['status'] = 'unavailable'
            metadata['attempted_sources'][-1]['reason'] = reason
            metadata['errors'].append({'source': 'store', 'error': reason})
            
        except Exception as e:
            error_msg = str(e)
            logger.warning("Store source failed: %s", error_msg, exc_info=True)
            metadata['attempted_sources'][-1]['status'] = 'error'
            metadata['attempted_sources'][-1]['error'] = error_msg
            metadata['errors'].append({'source': 'store', 'error': error_msg})
        
        # Try CDP Network source (alternative)
        try:
            logger.info("Attempting to use CDP Network source (priority 2)...")
            metadata['attempted_sources'].append({
                'source': 'network',
                'priority': 2,
                'status': 'attempting'
            })
            
            network_source = CDPNetworkChatSource(page)
            await network_source.init()
            
            metadata['selected_source'] = 'network'
            metadata['selection_reason'] = 'Store unavailable, using CDP Network as alternative'
            metadata['attempted_sources'][-1]['status'] = 'success'
            
            logger.info("✓ Selected CDP Network source (alternative - degraded from preferred)")
            return network_source, True, metadata  # Degraded from preferred
            
        except SourceUnavailableError as e:
            reason = str(e)
            logger.warning("CDP Network source unavailable: %s", reason)
            metadata['attempted_sources'][-1]['status'] = 'unavailable'
            metadata['attempted_sources'][-1]['reason'] = reason
            metadata['errors'].append({'source': 'network', 'error': reason})
            
        except Exception as e:
            error_msg = str(e)
            logger.warning("CDP Network source failed: %s", error_msg, exc_info=True)
            metadata['attempted_sources'][-1]['status'] = 'error'
            metadata['attempted_sources'][-1]['error'] = error_msg
            metadata['errors'].append({'source': 'network', 'error': error_msg})
        
        # Fallback to DOM source
        try:
            logger.info("Falling back to DOM source (priority 3)...")
            metadata['attempted_sources'].append({
                'source': 'dom',
                'priority': 3,
                'status': 'attempting'
            })
            
            dom_source = DOMChatSource(page)
            await dom_source.init()
            
            metadata['selected_source'] = 'dom'
            metadata['selection_reason'] = 'Store and CDP Network unavailable, using DOM fallback'
            metadata['attempted_sources'][-1]['status'] = 'success'
            
            logger.warning(
                "⚠ Selected DOM source (fallback - data quality may be reduced, "
                "IDs may be less reliable)"
            )
            return dom_source, True, metadata  # Degraded
            
        except Exception as e:
            error_msg = str(e)
            logger.error("All sources failed, DOM source also unavailable: %s", error_msg, exc_info=True)
            metadata['attempted_sources'][-1]['status'] = 'error'
            metadata['attempted_sources'][-1]['error'] = error_msg
            metadata['errors'].append({'source': 'dom', 'error': error_msg})
            
            raise SourceUnavailableError(
                f"All chat sources are unavailable. Errors: {metadata['errors']}"
            ) from e

