from os.path import join
from ...MPLogger import loggingclient

from time import sleep, time
from datetime import datetime
from urlparse import urlparse
import binascii
import base64
from selenium.common.exceptions import WebDriverException


def save_screenshot_b64(out_png_path, image_b64, logger):
    try:
        with open(out_png_path, 'wb') as f:
            f.write(base64.b64decode(image_b64.encode('ascii')))
    except Exception:
        logger.exception("Error while saving screenshot to %s"
                         % (out_png_path))
        return False
    return True


def capture_screenshots(visit_duration, **kwargs):
    """Capture screenshots every second."""
    driver = kwargs['driver']
    visit_id = kwargs['visit_id']
    manager_params = kwargs['manager_params']
    logger = loggingclient(*manager_params['logger_address'])
    screenshot_dir = manager_params['screenshot_path']
    landing_url = driver.current_url
    screenshot_base_path = join(screenshot_dir, "%d_%s" % (
        visit_id, urlparse(landing_url).hostname))
    last_image_crc = 0
    t_begin = time()
    for idx in xrange(0, visit_duration):
        quit_selenium = False
        phase = None
        t0 = time()
        try:
            quit_selenium = driver.execute_script(
                "return localStorage['openwpm-quit-selenium'];")
            quit_reason = driver.execute_script(
                "return localStorage['openwpm-quit-reason'];")
            phase = driver.execute_script(
                "return localStorage['openwpm-phase'];")
        except WebDriverException as exc:
            logger.warning(
                "Error while reading localStorage on %s Visit ID: %d %s"
                % (driver.current_url, visit_id, exc))

        if quit_selenium or driver.current_url == "about:blank":
            logger.info(
                "Received quit on %s Visit ID: %d "
                "phase: %s reason: %s signal: %s landing_url: %s" %
                (driver.current_url, visit_id, phase,
                 quit_reason, quit_selenium, landing_url))
            return

        try:
            img_b64 = driver.get_screenshot_as_base64()
        except Exception:
            logger.exception("Error while taking screenshot on %s Visit ID: %d"
                             % (driver.current_url, visit_id))
            sleep(max([0, 1-(time() - t0)]))  # try to spend 1s on each loop
            continue
        new_image_crc = binascii.crc32(img_b64)
        # check if the image has changed
        if new_image_crc == last_image_crc:
            continue
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        out_png_path = "%s_%s_%d" % (screenshot_base_path,
                                     timestamp, idx)
        save_screenshot_b64(out_png_path, img_b64, logger)
        last_image_crc = new_image_crc
        capture_duration = time() - t0
        logger.info(
            "Save_screenshot took %0.1f on %s Visit ID: %d Loop: %d Phase: %s"
            % (capture_duration, driver.current_url, visit_id, idx, phase))

        sleep(max([0, 1-capture_duration]))
        if (time() - t_begin) > visit_duration:  # timeout
            break
