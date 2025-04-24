from fastapi import APIRouter, Depends, UploadFile,File
import app.controllers.scrape as controller
from typing import List

router = APIRouter()

@router.post("/get-all-summary")
async def get_all_summary(
):
    try:
        scraped_data = await controller.run()
        message = "scraped successfully"
        return {
            "status": True,
            "message": message,
            "data": scraped_data
        }

    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }

@router.get("/get-all-analysis-report")
async def get_all_analysis_report(
):
    try:
        scraped_data = await controller.get_all_sr_letters()
        message = "All SR LETTERS fetched"
        return {
            "status": True,
            "message": message,
            "data": scraped_data
        }

    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }
    
@router.get("/get-all-SR-report")
async def get_all_sr_letter_by_id(
    letter_id: str
):
    try:
        scraped_data = await controller.get_all_sr_letters_by_id(letter_id)
        message = "SR LETTER fetched"
        return {
            "status": True,
            "message": message,
            "data": scraped_data
        }

    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }