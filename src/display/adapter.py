"""EPD display adapter for 4.26\" Waveshare e-ink screen.

This module provides a clean interface to the EPD hardware, abstracting
away low-level driver details and providing graceful degradation when
hardware is unavailable.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    pass


class RefreshMode(str, Enum):
    """Display refresh modes."""
    
    FULL = "full"
    PARTIAL = "partial"


class EPDAdapter:
    """Adapter for Waveshare 4.26\" e-ink display with 4-grayscale support.
    
    Handles hardware initialization, image buffering, and refresh operations.
    Falls back to simulation mode when hardware is unavailable.
    """
    
    def __init__(self, width: int = 800, height: int = 480) -> None:
        """Initialize EPD adapter.
        
        Args:
            width: Display width in pixels.
            height: Display height in pixels.
        """
        self._width = width
        self._height = height
        self._logger = logging.getLogger(self.__class__.__name__)
        self._epd = None
        self._hardware_available = False
        self._initialized = False
        
        # Try to import EPD driver.
        try:
            from src.lib.waveshare_epd import epd4in26
            self._epd_module = epd4in26
            self._hardware_available = True
            self._logger.info("EPD hardware driver loaded successfully")
        except (ImportError, OSError) as e:
            self._epd_module = None
            self._logger.warning(f"EPD hardware unavailable, running in simulation mode: {e}")
    
    def initialize(self, grayscale: bool = True) -> bool:
        """Initialize the display hardware.
        
        Args:
            grayscale: If True, initialize in 4-grayscale mode; otherwise 2-color mode.
        
        Returns:
            True if initialization succeeded, False otherwise.
        """
        if not self._hardware_available or self._epd_module is None:
            self._logger.info("Simulating EPD initialization (no hardware)")
            self._initialized = True
            return True
        
        try:
            self._epd = self._epd_module.EPD()
            
            if grayscale:
                self._logger.info("Initializing EPD in 4-grayscale mode...")
                result = self._epd.init_4GRAY()
            else:
                self._logger.info("Initializing EPD in 2-color mode...")
                result = self._epd.init()
            
            if result != 0:
                self._logger.error("EPD initialization failed")
                return False
            
            self._initialized = True
            self._logger.info("EPD initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"EPD initialization error: {e}")
            return False
    
    def display(self, image: Image.Image, mode: RefreshMode = RefreshMode.FULL) -> bool:
        """Display an image on the e-ink screen.
        
        Args:
            image: PIL Image object (should be in 'L' mode for grayscale).
            mode: Refresh mode (FULL or PARTIAL).
        
        Returns:
            True if display succeeded, False otherwise.
        """
        if not self._initialized:
            self._logger.warning("EPD not initialized, call initialize() first")
            return False
        
        # Validate image dimensions.
        if image.size != (self._width, self._height):
            self._logger.error(
                f"Image size mismatch: expected {self._width}x{self._height}, "
                f"got {image.width}x{image.height}"
            )
            return False
        
        # Simulation mode.
        if not self._hardware_available:
            self._logger.info(
                f"Simulating EPD display (mode={mode.value}, size={image.width}x{image.height})"
            )
            return True
        
        try:
            if mode == RefreshMode.FULL:
                return self._display_full(image)
            else:
                return self._display_partial(image)
                
        except Exception as e:
            self._logger.error(f"EPD display error: {e}")
            return False
    
    def _display_full(self, image: Image.Image) -> bool:
        """Perform full refresh display.
        
        Args:
            image: PIL Image in grayscale mode.
        
        Returns:
            True if succeeded.
        """
        if self._epd is None:
            self._logger.error("EPD instance not available")
            return False
        
        self._logger.info("Performing full 4-grayscale refresh...")
        
        # Convert PIL image to EPD buffer.
        buffer = self._epd.getbuffer_4Gray(image)
        
        # Display with 4-gray mode.
        self._epd.display_4Gray(buffer)
        
        self._logger.info("Full refresh completed")
        return True
    
    def _display_partial(self, image: Image.Image) -> bool:
        """Perform partial refresh display.
        
        Args:
            image: PIL Image in grayscale mode.
        
        Returns:
            True if succeeded.
        """
        if self._epd is None:
            self._logger.error("EPD instance not available")
            return False
        
        self._logger.info("Performing partial refresh...")
        
        # Convert to 1-bit for partial refresh (EPD limitation).
        # Note: Partial refresh on this hardware doesn't support 4-gray.
        buffer = self._epd.getbuffer(image)
        
        # Display with partial mode.
        self._epd.display_Partial(buffer)
        
        self._logger.info("Partial refresh completed")
        return True
    
    def clear(self) -> bool:
        """Clear the display to white.
        
        Returns:
            True if succeeded.
        """
        if not self._initialized:
            self._logger.warning("EPD not initialized")
            return False
        
        if not self._hardware_available:
            self._logger.info("Simulating EPD clear")
            return True
        
        if self._epd is None:
            self._logger.error("EPD instance not available")
            return False
        
        try:
            self._logger.info("Clearing display...")
            self._epd.Clear()
            self._logger.info("Display cleared")
            return True
        except Exception as e:
            self._logger.error(f"EPD clear error: {e}")
            return False
    
    def sleep(self) -> bool:
        """Put the display into deep sleep mode.
        
        Returns:
            True if succeeded.
        """
        if not self._initialized:
            self._logger.warning("EPD not initialized")
            return False
        
        if not self._hardware_available:
            self._logger.info("Simulating EPD sleep")
            return True
        
        if self._epd is None:
            self._logger.error("EPD instance not available")
            return False
        
        try:
            self._logger.info("Putting EPD into sleep mode...")
            self._epd.sleep()
            self._initialized = False
            self._logger.info("EPD entered sleep mode")
            return True
        except Exception as e:
            self._logger.error(f"EPD sleep error: {e}")
            return False
    
    @property
    def is_hardware_available(self) -> bool:
        """Check if actual hardware is available."""
        return self._hardware_available
    
    @property
    def is_initialized(self) -> bool:
        """Check if display is initialized."""
        return self._initialized
