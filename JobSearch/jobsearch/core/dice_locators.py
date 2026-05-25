# dice_locators.py

from dataclasses import dataclass


@dataclass(frozen=True)
class DiceLocators:
    # Page-level
    BODY_TAG = "//body"

    # Search inputs
    JOB_TITLE_INPUT = "//input[contains(@placeholder, 'Job title')]"
    LOCATION_INPUT = "//input[contains(@placeholder, 'Location')]"

    # Cookies
    COOKIES_ALLOW_ALL_BUTTON = "//button[contains(., 'Allow all')]"

    # Filters
    ALL_FILTERS_BUTTON = "//button[contains(., 'All Filters')]"
    FILTER_DRAWER = "//button[normalize-space(.) = 'Clear filters']/following-sibling::button[normalize-space(.) = 'Apply filters']"
    FILTER_SECTION_BUTTON = FILTER_DRAWER + "//button[contains(., '{section}')]"
    FILTER_LABEL = "//label[contains(., '{label}')]"
    APPLY_FILTERS_BUTTON = FILTER_DRAWER + "//button[contains(., 'Apply')]"
    SEARCH = "//button[@data-testid = 'job-search-search-bar-search-button']"

    # Results list items
    LIST_ITEM = "//div[@role='listitem']"
    LIST_ITEM_LINK = ".//a"

    # Detail page elements
    TITLE = "//h1[@data-cy='jobTitle'] | //h1[contains(@class, 'jobTitle')]"
    COMPANY = (
        "//a[@data-cy='companyNameLink'] "
        "| //*[@data-cy='companyName'] "
        "| //*[@class='companyName']"
    )
    LOCATION = (
        "//li[@data-cy='location'] "
        "| //*[@data-cy='location'] "
        "| //*[@class='location']"
    )
    JOB_TYPE = (
        "//li[@data-cy='workFromHomeLabel']"
        " | //*[@class='workLocation']"
        " | //*[contains(., 'Remote') or contains(., 'Hybrid') "
        "        or contains(., 'On-site') or contains(., 'Onsite')]"
    )
    POSTED = (
        "//li[@data-cy='postedDate'] "
        "| //*[@data-cy='postedDate'] "
        "| //*[@class='posted']"
    )
    RATE = (
        "//*[@data-cy='compensationText'] "
        "| //*[@class='compensation'] "
        "|//*[contains(text(), '$')]"
    )
