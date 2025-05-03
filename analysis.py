import pandas as pd

df = pd.read_csv("embedding_status.csv")

unique_video_ids = df["video_id"].unique()

unique_video_ids_list = unique_video_ids.tolist()

print(unique_video_ids_list)
print(len(unique_video_ids_list))
