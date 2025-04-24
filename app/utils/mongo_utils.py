from fastapi import HTTPException, status
from pymongo import ASCENDING, DESCENDING
from datetime import datetime
from app.database import SR_Letters , Analysis, Changes
from typing import Optional
from datetime import datetime, timedelta
from typing_extensions import Any
import app.helpers.helper as helper
from fastapi import HTTPException, status
import json

async def save_letter_info(SR_letters):

    SR_letters = await helper.remove_backticks(SR_letters)
    SR_letters = json.loads(SR_letters)
    try:
        for letter in SR_letters:
            existing_letter = SR_Letters.find_one({"letter_id": letter["letter_id"]})
            
            if existing_letter:
                print(f"Skipping duplicate letter: {letter['letter_id']}")
                continue
            
            SR_Letters.insert_one(letter)
            print(f"Saved new letter: {letter['letter_id']}")
        
        return {"message": "SR letters processed successfully"}
    
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Something went wrong while saving letters in the database. {e}"
        )
    
# def save_analysis_info(analysis):
#     try:
#         for analysis_info in analysis:
#             existing_analysis = Analysis.find_one({"analysis_id": analysis_info["analysis_id"]})
            
#             if existing_analysis:
#                 print(f"Skipping duplicate analysis: {analysis_info['analysis_id']}")
#                 continue
            
#             Analysis.insert_one(analysis_info)
#             print(f"Saved new analysis: {analysis_info['analysis_id']}")
        
#         return {"message": "Analysis processed successfully"}
    
#     except Exception as e:
#         print(f"Error: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Something went wrong while saving analysis in the database. {e}"
#         )

async def get_all_sr_letters_by_id(letter_id):
    try:
        if letter_id:
            sr_letter = SR_Letters.find_one(filter={"letter_id": letter_id},
            projection={"_id": 0,})
            if sr_letter:
                return sr_letter
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="SR Letter not found"
                )
        else:
            sr_letters = SR_Letters.find()
            return sr_letters
    
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Something went wrong while fetching SR Letters from the database. {e}"
        )

async def get_all_sr_letters():
    try:
        sr_letters = list(SR_Letters.find(projection={
                "_id": 0
            }))
        # result = [doc["letter_id"] for doc in sr_letters]
        return sr_letters
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Something went wrong while fetching SR Letter IDs from the database. {e}"
        )
