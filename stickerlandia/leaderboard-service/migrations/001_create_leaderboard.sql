CREATE TABLE IF NOT EXISTS leaderboard_scores (
    user_id VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL DEFAULT '',
    sticker_count INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leaderboard_sticker_count ON leaderboard_scores (sticker_count DESC);
CREATE INDEX IF NOT EXISTS idx_leaderboard_display_name ON leaderboard_scores (display_name);
