from langchain_community.utilities import SQLDatabase

if __name__ == '__main__':
    db = SQLDatabase.from_uri('sqlite:///../chinook.db')
    print(db.get_usable_table_names())
    res = db.run("select * from artists limit 10")
    print(res)