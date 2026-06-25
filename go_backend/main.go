package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/joho/godotenv"
	_ "github.com/microsoft/go-mssqldb"
)

type OmsetData struct {
	TransaksiID                   string  `json:"transaksiid"`
	Tanggal                       string  `json:"tanggal"`
	Nama_Sales                    string  `json:"nama_sales"`
	Nama_Produk                   string  `json:"nama_produk"`
	Kuantitas                     int     `json:"kuantitas"`
	Harga_Satuan                  float64 `json:"harga_satuan"`
	Total_Pembayaran              float64 `json:"total_pembayaran"`
	Prediksi_Omset_HariBerikutnya float64 `json:"prediksi_omset_hariberikutnya"`
}

func getOmset(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With")

		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}

		query := `
			SELECT 	TransaksiID, Tanggal, Nama_Produk,
					Total_Pembayaran, Prediksi_Omset_HariBerikutnya
			FROM Fact_Clean_Penjualan
		`
		rows, err := db.Query(query)

		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		defer rows.Close()

		var hasil []OmsetData

		for rows.Next() {
			var data OmsetData
			var tanggalWaktu []byte

			err := rows.Scan(&data.TransaksiID, &tanggalWaktu, &data.Nama_Produk, &data.Total_Pembayaran, &data.Prediksi_Omset_HariBerikutnya)

			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}

			if len(tanggalWaktu) >= 10 { // jika tanggal tidak NaN atau nil
				data.Tanggal = string(tanggalWaktu[:10])
			}

			hasil = append(hasil, data)
		}

		json.NewEncoder(w).Encode(hasil)
	}
}

func main() {
	err := godotenv.Load("../.env")

	if err != nil {
		log.Fatal(".env file tidak ditemukan")
	}

	setKoneksi := fmt.Sprintf("server=%s;database=%s;user id=%s;password=%s;encrypt=disable", os.Getenv("DB_SERVER"), os.Getenv("DB_NAME"), os.Getenv("DB_USER"), os.Getenv("DB_PASSWORD"))

	db, err := sql.Open("sqlserver", setKoneksi)

	if err != nil {
		log.Fatal("Gagal Terhubung ke SQL Server ERR: ", err.Error())
		return
	}
	defer db.Close()

	http.HandleFunc("/omsetPenjualan", getOmset(db))

	fmt.Println("Backend Steady, test di postman http://localhost:8080/omsetPenjualan")

	log.Fatal(http.ListenAndServe(":8080", nil))
}
