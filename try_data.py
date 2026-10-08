import data_manager

print("create:", data_manager.create_user("Tester_1", "longpassword1"))
print("same name:", data_manager.create_user("tester_1", "otherpassword2"))
print("good login:", data_manager.verify_login("TESTER_1", "longpassword1"))
print("bad login:", data_manager.verify_login("tester_1", "wrong"))
print("too long:", data_manager.create_user("tester_2", "x" * 80))
ok, user_id = data_manager.verify_login("tester_1", "longpassword1")

record = {"user_id": user_id, "image_name": "t.jpg", "calorie_limit": 500, "diet": "none",
          "detected_items": [{"name": "rice"}],
          "accepted": [{"name": "Egg rice", "calories": 450.0, "status": "accepted",
                        "score": 85.0, "leftovers_used": 2, "reasons": []}],
          "rejected": []}
print("save:", data_manager.save_record(record))
print("recent:", data_manager.load_recent(user_id))
print("filter:", data_manager.filter_recipes(user_id, max_calories=500))
print("other user:", data_manager.filter_recipes(user_id + 99))